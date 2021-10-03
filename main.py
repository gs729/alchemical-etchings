import csv
import argparse
import itertools
from typing import Dict, List
from enum import Enum

# Positions of id, name, d2_class, exotic, slot, mob, res, rec, dis, int, str in the CSV Row
CSV_ROW_DEFN = [2, 0, 7, 4, 5, 27, 28, 29, 30, 31, 32]

# Argument parsing
parser = argparse.ArgumentParser(description='List armor to dismantle')
parser.add_argument('--mods', action='store_true', help='Enable mods')
parser.add_argument('--tier', type=int, help='Minimum build tier')
args = parser.parse_args()
BASE_MODS_ENABLED = args.mods
if args.tier is None:
    TIER_LIMIT = 31
    if BASE_MODS_ENABLED:
        TIER_LIMIT += 5
else:
    TIER_LIMIT = args.tier


class Stat(Enum):
    MOBILITY = 0
    RESILIENCE = 1
    RECOVERY = 2
    DISCIPLINE = 3
    INTELLECT = 4
    STRENGTH = 5


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
        self.mobility = mobility
        self.resilience = resilience
        self.recovery = recovery
        self.discipline = discipline
        self.intellect = intellect
        self.strength = strength
        self.mark: bool = False

    def __le__(self, other):
        if (
            self.mobility <= other.mobility
            and self.resilience <= other.resilience
            and self.recovery <= other.recovery
            and self.discipline <= other.discipline
            and self.intellect <= other.intellect
            and self.strength <= other.strength
        ):
            return True
        else:
            return False

    def __ge__(self, other):
        if (
            self.mobility >= other.mobility
            and self.resilience >= other.resilience
            and self.recovery >= other.recovery
            and self.discipline >= other.discipline
            and self.intellect >= other.intellect
            and self.strength >= other.strength
        ):
            return True
        else:
            return False

    def __eq__(self, other):
        if (
            self.mobility == other.mobility
            and self.resilience == other.resilience
            and self.recovery == other.recovery
            and self.discipline == other.discipline
            and self.intellect == other.intellect
            and self.strength == other.strength
        ):
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
        params[0] = int(params[0].strip('"'))
        if params[3].lower() == "exotic":
            params[3] = True
        else:
            params[3] = False
        params[-1] = int(params[-1])
        params[-2] = int(params[-2])
        params[-3] = int(params[-3])
        params[-4] = int(params[-4])
        params[-5] = int(params[-5])
        params[-6] = int(params[-6])
        return cls(*params)


class Build(List):
    def __init__(self, armor_list: List[Armor], mods_used: int = 0):
        self.extend(armor_list)
        self.mods_used = mods_used
        self.stats = [0, 0, 0, 0, 0, 0]
        for armor in self:
            self.stats[Stat.MOBILITY.value] += armor.mobility
            self.stats[Stat.RESILIENCE.value] += armor.resilience
            self.stats[Stat.RECOVERY.value] += armor.recovery
            self.stats[Stat.DISCIPLINE.value] += armor.discipline
            self.stats[Stat.INTELLECT.value] += armor.intellect
            self.stats[Stat.STRENGTH.value] += armor.strength
        
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
        individual_tiers = [0, 0, 0, 0, 0, 0,]
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
    
    def mark(build):
        for armor in build:
            armor.mark = True

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


armor_lists: List[List[Armor]] = [[], [], [], [], []]

with open("armor.csv") as csvfile:
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

# Add generic class items
armor_lists[4].append(
    Armor(0, "Class Item", "Hunter", False, "Class Item", 0, 0, 0, 0, 0, 0)
)
armor_lists[4].append(
    Armor(0, "Class Item", "Warlock", False, "Class Item", 0, 0, 0, 0, 0, 0)
)
armor_lists[4].append(
    Armor(0, "Class Item", "Titan", False, "Class Item", 0, 0, 0, 0, 0, 0)
)

# Iterate through all possible armor combinations                    
for armor_set in itertools.product(*armor_lists):
    build = Build(armor_set)
    if build.is_valid():
        if build.calculate_tier() >= TIER_LIMIT:
            build.mark()

# Save at least one exotic
exotic_list = []
for armor in armor_lists[0] + armor_lists[1] + armor_lists[2] + armor_lists[3]:
    if armor.is_exotic:
        exotic_list.append(armor)
exotic_lists_by_name: Dict[str, List[Armor]] = {}
for armor in exotic_list:
    if armor.name in exotic_lists_by_name:
        exotic_lists_by_name[armor.name].append(armor)
    else:
        exotic_lists_by_name[armor.name] = [armor]

for name in exotic_lists_by_name:
    if all([not armor.mark for armor in exotic_lists_by_name[name]]):
        for armor in exotic_lists_by_name[name]:
            armor.mark = True

# Save all class items:
for armor in armor_lists[0] + armor_lists[1] + armor_lists[2] + armor_lists[3]:
    if armor.slot.lower() in ["hunter cloak", "warlock bond", "titan mark"]:
        armor.mark = True

query = str()
unmarked_armor_counter = 0
for armor in armor_lists[0] + armor_lists[1] + armor_lists[2] + armor_lists[3]:
    if not armor.mark:
        unmarked_armor_counter += 1
        query += " or id:" + str(armor.id)
query = query[4:]

print("\n" + query + "\n")
print("Number of junk armor pieces:", unmarked_armor_counter)
