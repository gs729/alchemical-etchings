import csv
import argparse
import hashlib
import itertools
import pickle
from tqdm import tqdm
from typing import Dict, List
from enum import Enum

# Positions of id, name, d2_class, exotic, slot, mob, res, rec, dis, int, str in the CSV Row
CSV_ROW_DEFN = [2, 0, 7, 4, 5, 27, 28, 29, 30, 31, 32]

# Argument parsing
parser = argparse.ArgumentParser(description="List armor to dismantle")
parser.add_argument("--mods", action="store_true", help="Enable mods")
parser.add_argument("--tier", type=int, help="Minimum build tier")
parser.add_argument("armor_file", type=str, help="armor.csv file from DIM")
args = parser.parse_args()
BASE_MODS_ENABLED = args.mods
if args.tier is None:
    TIER_LIMIT = 31
    if BASE_MODS_ENABLED:
        TIER_LIMIT += 5
else:
    TIER_LIMIT = args.tier
ARMOR_FILE = args.armor_file


class Stat(Enum):
    MOBILITY = 0
    RESILIENCE = 1
    RECOVERY = 2
    DISCIPLINE = 3
    INTELLECT = 4
    STRENGTH = 5


# Mods
class Mod:
    registry = []

    def __init__(self, name: str, energy_cost: int, stat_delta: List[int]):
        self.name = name
        self.energy_cost = energy_cost
        self.stat_delta = stat_delta
        for idx, mod in enumerate(self.registry):
            if mod.energy_cost > energy_cost:
                break
        self.registry.insert(idx, self)

    @classmethod
    def mod_for_delta(
        cls, stat_delta: List[int] = [10, 10, 10, 10, 10, 10], energy_budget: int = 10
    ):
        """Takes a stat delta and returns the mod that would best help minimise it

        Returns:
            Mod: Mod that best works towards minimising the delta
        """
        candidate_mods = [
            mod for mod in cls.registry if mod.energy_cost <= energy_budget
        ]
        current_best_stat_delta = stat_delta
        for mod in candidate_mods:
            if stat_delta - mod.stat_delta < current_best_stat_delta:
                pass


class Armor:
    def __init__(
        self,
        id,
        name,
        d2_class,
        is_exotic,
        slot,
        mobility,
        resilience,
        recovery,
        discipline,
        intellect,
        strength,
    ):
        self.id = id
        self.name = name
        self.d2_class = d2_class
        self.is_exotic = is_exotic
        self.slot = slot
        self.mark: int = 0
        self.stats = [0] * 6
        self.stats[Stat.MOBILITY.value] = mobility
        self.stats[Stat.RESILIENCE.value] = resilience
        self.stats[Stat.RECOVERY.value] = recovery
        self.stats[Stat.DISCIPLINE.value] = discipline
        self.stats[Stat.INTELLECT.value] = intellect
        self.stats[Stat.STRENGTH.value] = strength

    def __le__(self, other):
        if all([self.stats[i] <= other.stats[i] for i in range(6)]):
            return True
        else:
            return False

    def __ge__(self, other):
        if all([self.stats[i] >= other.stats[i] for i in range(6)]):
            return True
        else:
            return False

    def __eq__(self, other):
        if all([self.stats[i] == other.stats[i] for i in range(6)]):
            return True
        else:
            return False

    def __lt__(self, other):
        if self <= other and self != other:
            return True
        else:
            return False

    def __gt__(self, other):
        if self >= other and self != other:
            return True
        else:
            return False

    def __repr__(self):
        return (
            self.__class__.__name__
            + "("
            + " ".join(
                [
                    str(self.id),
                    '"' + str(self.name) + '"',
                    str(self.d2_class),
                    str(self.is_exotic),
                    str(self.slot),
                    str(self.mobility),
                    str(self.resilience),
                    str(self.recovery),
                    str(self.discipline),
                    str(self.intellect),
                    str(self.strength),
                ]
            )
            + ")"
        )

    @classmethod
    def from_csv_row(cls, csv_row):
        params = [csv_row[i] for i in CSV_ROW_DEFN]
        self = cls(*params)
        self.id = int(self.id.strip('"'))
        if self.is_exotic.lower() == "exotic":
            self.is_exotic = True
        else:
            self.is_exotic = False
        self.stats = [int(stat) for stat in self.stats]
        return self


class Build(List):
    def __init__(self, armor_list: List[Armor], mods_used: int = 0):
        self.extend(armor_list)
        self.mods_used = mods_used
        self.stats = [0, 0, 0, 0, 0, 0]
        for armor in self:
            for stat in Stat:
                self.stats[stat.value] += armor.stats[stat.value]

    def add_mods(build):
        for idx, tier in enumerate(build.stats):
            # This formula checks if a tier can benefit from a +5 mod
            if tier % 10 > 5 and build.mods_used < 5:
                build.mods_used += 1
                build.stats[idx] += 5
        for mod_no in range(5 - build.mods_used):
            for idx, tier in enumerate(build.stats):
                if tier < 100:
                    build.stats[idx] += 10
                    build.mods_used += 1
                    break
        return build

    def calculate_tier(build):
        # Calculate effective tiers
        individual_tiers = [
            0,
            0,
            0,
            0,
            0,
            0,
        ]
        for idx in range(len(build.stats)):
            if BASE_MODS_ENABLED:
                build.add_mods()
            individual_tiers[idx] = build.stats[idx] // 10
            individual_tiers[idx] = (
                10 if individual_tiers[idx] > 10 else individual_tiers[idx]
            )
        total = sum(individual_tiers)
        # Account for armor masterworks
        total += 6
        return total

    def mark(build, tier):
        for armor in build:
            if armor.mark <= tier:
                armor.mark = tier

    def is_valid(build):
        if not all([item.d2_class == build[0].d2_class for item in build]):
            return False
        number_of_exotics = 0
        for armor in build:
            if armor.is_exotic:
                number_of_exotics += 1
        if number_of_exotics > 1:
            return False
        return True


class try_achieve_build(list):
    def __init__(self, build: List[Armor], mods_used: int = 0):
        self.extend(build)
        self.mods_used = mods_used

    def _general_stat_func(self, stat_name: str, stat: int):
        while True:
            gulf = self[int(Stat(stat_name.upper()))] - stat
            if gulf > 5:
                self.mods_used += 1
                self[int(Stat(stat_name.upper()))] += 10
            else:
                break
        return self

    def mobility(self, mobility: int):
        return self._general_stat_func("mobility")

    def resilience(self, resilience: int):
        return self._general_stat_func("resilience")

    def recovery(self, recovery: int):
        return self._general_stat_func("recovery")

    def discipline(self, discipline: int):
        return self._general_stat_func("discipline")

    def intellect(self, intellect: int):
        return self._general_stat_func("intellect")

    def strength(self, strength: int):
        return self._general_stat_func("strength")


def generic_class_items() -> List[Armor]:
    # Add generic class items
    li = []
    li.append(Armor(0, "Class Item", "Hunter", False, "Class Item", 0, 0, 0, 0, 0, 0))
    li.append(Armor(0, "Class Item", "Warlock", False, "Class Item", 0, 0, 0, 0, 0, 0))
    li.append(Armor(0, "Class Item", "Titan", False, "Class Item", 0, 0, 0, 0, 0, 0))
    return li


def save_exotics(armor_list):
    # List all exotics
    exotic_list = []
    for armor in armor_list:
        if armor.is_exotic:
            exotic_list.append(armor)

    # Sort exotics by name
    exotic_lists_by_name: Dict[str, List[Armor]] = {}
    for armor in exotic_list:
        if armor.name in exotic_lists_by_name:
            exotic_lists_by_name[armor.name].append(armor)
        else:
            exotic_lists_by_name[armor.name] = [armor]

    # if all exotics with a name are not marked to be saved
    # mark all of them to show they shouldn't be dismantled
    for name in exotic_lists_by_name:
        if all([armor.mark < TIER_LIMIT for armor in exotic_lists_by_name[name]]):
            for armor in exotic_lists_by_name[name]:
                armor.mark = 9999


def save_class_items(armor_list):
    for armor in armor_list:
        if not (
            armor.slot.lower() == "helmet"
            or armor.slot.lower() == "gauntlets"
            or armor.slot.lower() == "chest armor"
            or armor.slot.lower() == "leg armor"
        ):
            armor.mark = 9999


armor_lists: List[List[Armor]] = [[], [], [], [], []]

with open(ARMOR_FILE, "rb", buffering=0) as csvfile:
    sha1 = hashlib.sha1()
    while True:
        data = csvfile.read(4096)
        if not data:
            break
        sha1.update(data)
    csvfile_hash = sha1.hexdigest()

try:
    # Load pickle file as cache here
    with open(str(csvfile_hash) + ".pickle", "rb") as processed_armor:
        combined_armor_list = pickle.load(processed_armor)
except FileNotFoundError:
    with open(ARMOR_FILE) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for idx, row in enumerate(reader):
            if idx == 0:
                continue
            armor = Armor.from_csv_row(row)
            if armor.slot.lower() == "helmet":
                slot = 0
            elif armor.slot.lower() == "gauntlets":
                slot = 1
            elif armor.slot.lower() == "chest armor":
                slot = 2
            elif armor.slot.lower() == "leg armor":
                slot = 3
            else:
                pass
            armor_lists[slot].append(armor)

    armor_lists[4] = generic_class_items()

    total_armor_pieces = (
        len(armor_lists[0])
        + len(armor_lists[1])
        + len(armor_lists[2])
        + len(armor_lists[3])
        + len(armor_lists[4])
    )
    total_armor_sets = (
        len(armor_lists[0])
        * len(armor_lists[1])
        * len(armor_lists[2])
        * len(armor_lists[3])
        * len(armor_lists[4])
    )
    for armor_set in tqdm(itertools.product(*armor_lists), total=total_armor_sets):
        build = Build(armor_set)
        if build.is_valid():
            build.mark(build.calculate_tier())

    combined_armor_list = (
        armor_lists[0]
        + armor_lists[1]
        + armor_lists[2]
        + armor_lists[3]
        + armor_lists[4]
    )
    # Create a pickle file as a cache here
    with open(str(csvfile_hash) + ".pickle", "wb") as processed_armor:
        pickle.dump(combined_armor_list, processed_armor)


save_exotics(combined_armor_list)
save_class_items(combined_armor_list)


# Generate a DIM query to highlight all useless armor
query = str()
unmarked_armor_counter = 0


for armor in combined_armor_list:
    if armor.mark < TIER_LIMIT:
        unmarked_armor_counter += 1
        query += " or id:" + str(armor.id)
query = query[4:]

print("\n" + query + "\n")
print("Number of junk armor pieces:", unmarked_armor_counter)
