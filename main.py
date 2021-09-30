import csv
from typing import Dict, List
import pprint

# Positions of id, name, d2_class, exotic, slot, mob, res, rec, dis, int, str in the CSV Row
CSV_ROW_DEFN = [2, 0, 7, 4, 5, 27, 28, 29, 30, 31, 32]

TIER_LIMIT = 30


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


def build_is_valid(build: List[Armor]):
    if not all([item.d2_class == build[0].d2_class for item in build]):
        return False
    number_of_exotics = 0
    for armor in build:
        if armor.is_exotic:
            number_of_exotics += 1
    if number_of_exotics > 1:
        return False
    return True


def calc_build_tier(build: List[Armor]):
    individual_tiers = [0, 0, 0, 0, 0, 0]
    for armor in build:
        individual_tiers[0] += armor.mobility
        individual_tiers[1] += armor.resilience
        individual_tiers[2] += armor.recovery
        individual_tiers[3] += armor.discipline
        individual_tiers[4] += armor.intellect
        individual_tiers[5] += armor.strength
    # Calculate effective tiers
    for idx in range(len(individual_tiers)):
        individual_tiers[idx] = individual_tiers[idx] // 10
        individual_tiers[idx] = (
            10 if individual_tiers[idx] > 10 else individual_tiers[idx]
        )
    total = sum(individual_tiers)
    # Account for armor masterworks
    total += 5
    return total


def mark_build(build: List[Armor]):
    for armor in build:
        armor.mark = True


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

build_counter = 0
unmarked_armor_counter = 0

for zero in armor_lists[0]:
    for one in armor_lists[1]:
        for two in armor_lists[2]:
            for three in armor_lists[3]:
                for four in armor_lists[4]:
                    build = [zero, one, two, three, four]
                    if build_is_valid(build):
                        if calc_build_tier(build) >= TIER_LIMIT:
                            mark_build(build)
                            build_counter += 1

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
for armor in armor_lists[0] + armor_lists[1] + armor_lists[2] + armor_lists[3]:
    if not armor.mark:
        unmarked_armor_counter += 1
        query += " or id:" + str(armor.id)
query = query[4:]

print(query)
