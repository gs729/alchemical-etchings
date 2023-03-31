import argparse
import csv
import hashlib
import itertools
import pickle
from enum import Enum
from typing import Dict, List

import clipboard
from tqdm import tqdm

# Positions of id, name, d2_class, exotic, slot, mob, res, rec, dis, int, str in the CSV Row
CSV_ROW_DEFN = [
    2,  # id
    0,  # name
    7,  # d2_class
    4,  # is_exotic
    5,  # slot
    24,  # mobility
    25,  # resilience
    26,  # recovery
    27,  # discipline
    28,  # intellect
    29,  # strength
    3,  # tag
    12,  # locked
    10,  # masterwork_tier
    31,  # is_artifice
]


# Argument parsing
parser = argparse.ArgumentParser(description="List armor to dismantle")
parser.add_argument("--hunter", action="store_true", help="Only process hunter armor")
parser.add_argument("--warlock", action="store_true", help="Only process warlock armor")
parser.add_argument("--titan", action="store_true", help="Only process titan armor")
parser.add_argument(
    "--bottom",
    type=int,
    help=("Prints the bottom x armor pieces"),
)
parser.add_argument("armor_file", type=str, help="armor.csv file from DIM")
args = parser.parse_args()
BOTTOM = args.bottom
ARMOR_FILE = args.armor_file

if args.hunter:
    CLASS = "Hunter"
elif args.warlock:
    CLASS = "Warlock"
elif args.titan:
    CLASS = "Titan"
else:
    CLASS = "Any"


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
        tag,
        locked,
        masterwork_tier,
        is_artifice,
    ):
        self.id = id
        self.name = name
        self.d2_class = d2_class
        self.is_exotic = is_exotic
        self.slot = slot
        self.mark: int = 0
        self.score: float
        self.stats = [0] * 6
        self.stats[Stat.MOBILITY.value] = int(mobility)
        self.stats[Stat.RESILIENCE.value] = int(resilience)
        self.stats[Stat.RECOVERY.value] = int(recovery)
        self.stats[Stat.DISCIPLINE.value] = int(discipline)
        self.stats[Stat.INTELLECT.value] = int(intellect)
        self.stats[Stat.STRENGTH.value] = int(strength)
        self.tag = tag.lower()
        self.locked = str(locked).lower() == "true"
        self.is_masterworked = int(masterwork_tier) == 10
        self.is_artifice = is_artifice
        if sum(self.stats) > 72:
            raise ValueError("Armor stats cannot exceed 72. {}".format(self.stats))

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
                    str(self.stats),
                    str(self.tag),
                    "Locked" if self.locked else "Unlocked",
                    "Masterworked" if self.is_masterworked else "Unmasterworked,",
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
        if self.is_artifice.lower() == "artifice":
            self.is_artifice = True
        else:
            self.is_artifice = False
        self.stats = [int(stat) for stat in self.stats]
        return self


class Build(List):
    def __init__(
        self, armor_list: List[Armor], mods_used: int = 0, artifice_mods_used: int = 0
    ):
        self.extend(armor_list)
        self.mods_used = mods_used
        self.artifice_slots = sum([1 for armor in self if armor.is_artifice])
        self.artifice_mods_used = artifice_mods_used
        self.stats = [0, 0, 0, 0, 0, 0]
        for armor in self:
            for stat in Stat:
                self.stats[stat.value] += armor.stats[stat.value]

    def add_mods(build):
        for artifice_mod_no in range(build.artifice_slots - build.artifice_mods_used):
            for idx, tier in enumerate(build.stats):
                if (
                    tier < 100
                    and (
                        (tier % 10)
                        + 3 * (build.artifice_slots - build.artifice_mods_used)
                    )
                    > 10
                ):
                    build.stats[idx] += 3
                    build.artifice_mods_used += 1
                    break
        for artifice_mod_no in range(build.artifice_slots - build.artifice_mods_used):
            for idx, tier in enumerate(build.stats):
                if (
                    tier < 100
                    and (
                        (tier % 5)
                        + 3 * (build.artifice_slots - build.artifice_mods_used)
                    )
                    > 5
                ):
                    build.stats[idx] += 3
                    build.artifice_mods_used += 1
                    break
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
        individual_tiers = [0] * 6
        for idx in range(len(build.stats)):
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


def generic_class_items() -> List[Armor]:
    # Add generic class items
    li = []
    for class_name in ["Hunter", "Warlock", "Titan"]:
        li.append(
            Armor(
                0,
                "Class Item",
                class_name,
                False,
                "Class Item",
                0,
                0,
                0,
                0,
                0,
                0,
                "",
                "FALSE",
                10,
                True,
            )
        )
    return li


def sort_by_score(armor):
    return armor.score


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
        if all(
            [armor_list.index(armor) < BOTTOM for armor in exotic_lists_by_name[name]]
        ):
            for armor in exotic_lists_by_name[name]:
                armor.score = 9999
    armor_list.sort(key=sort_by_score)


def save_class_items(armor_list):
    for armor in armor_list:
        if not (
            armor.slot.lower() == "helmet"
            or armor.slot.lower() == "gauntlets"
            or armor.slot.lower() == "chest armor"
            or armor.slot.lower() == "leg armor"
        ):
            armor.score = 9999
    armor_list.sort(key=sort_by_score)


def save_tagged(armor_list):
    for armor in armor_list:
        if armor.tag != "":
            armor.score = 9999
    armor_list.sort(key=sort_by_score)


def save_locked(armor_list):
    for armor in armor_list:
        if armor.locked:
            armor.score = 9999
    armor_list.sort(key=sort_by_score)


def save_masterworked(armor_list):
    for armor in armor_list:
        if armor.is_masterworked:
            armor.score = 9999
    armor_list.sort(key=sort_by_score)


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
    try:
        # Load pickle file as cache here
        with open(str(csvfile_hash) + CLASS + ".pickle", "rb") as processed_armor:
            combined_armor_list = pickle.load(processed_armor)
    except FileNotFoundError:
        with open(str(csvfile_hash) + "Any" + ".pickle", "rb") as processed_armor:
            combined_armor_list = pickle.load(processed_armor)
except FileNotFoundError:
    with open(ARMOR_FILE) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for idx, row in enumerate(reader):
            if idx == 0:
                continue
            try:
                armor = Armor.from_csv_row(row)
            except Exception as e:
                print("Error with armor row: " + str(row))
                raise e
            if not (armor.d2_class == CLASS or CLASS == "Any"):
                continue
            if armor.slot.lower() == "helmet":
                slot = 0
            elif armor.slot.lower() == "gauntlets":
                slot = 1
            elif armor.slot.lower() == "chest armor":
                slot = 2
            elif armor.slot.lower() == "leg armor":
                slot = 3
            else:
                continue
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
    with open(str(csvfile_hash) + CLASS + ".pickle", "wb") as processed_armor:
        pickle.dump(combined_armor_list, processed_armor)


for armor in combined_armor_list:
    if armor.slot == 4:
        continue
    armor.score = (
        (armor.mark - 35) * 2  # 0 to 4
        # Weighted stat total score:
        # Old Formula:
        # + (sum(armor.stats) - 62) * 2  # 0 to 12
        # New formula:
        # The x in x ** 0.5 is the pivot, 72 - x scores 0, 72 scores 1
        # Scores 0 to 20 but mean closer to 3.33 to 4.44
        # Also includes artifice armor in the total since they are free stats
        + (13**0.8 - (72 - sum(armor.stats) + (3 * int(armor.is_artifice))) ** 0.8)
        / 13**0.8
        * 20
        # Meta dependent scores:
        + (armor.stats[Stat.RECOVERY.value] - 2) * 0.2  # 0 to 5.6
        # Spike score to allow flexibility:
        + (sum(armor.stats[:3]) - min(armor.stats[:3]) - 16) * 0.35  # 0 to 5.6
        + (sum(armor.stats[3:]) - min(armor.stats[3:]) - 16) * 0.35  # 0 to 5.6
        # Artifice score to increase flexibility:
        + 2 * int(armor.is_artifice)  # 0 to 2
    )


combined_armor_list.sort(key=sort_by_score)
save_class_items(combined_armor_list)
save_tagged(combined_armor_list)
save_locked(combined_armor_list)
save_masterworked(combined_armor_list)
# Note: Save exotics needs to be last since
# it saves those about to be marked for dismantling
id_list = [[]]
while True:
    id_list.append([])
    for idx, armor in enumerate(combined_armor_list):
        if idx < BOTTOM:
            id_list[-1].append(armor.id)
    if id_list[-1] == id_list[-2]:
        break
    save_exotics(combined_armor_list)

# Generate a DIM query to highlight all useless armor
query = str()
unmarked_armor_counter = 0


for idx, armor in enumerate(combined_armor_list):
    if idx < BOTTOM:
        unmarked_armor_counter += 1
        print(armor)
        query += " or id:" + str(armor.id)
query = query[4:]

print("\n\nNumber of junk armor pieces:", unmarked_armor_counter)

print("\n" + query + "\n")
clipboard.copy(query)
