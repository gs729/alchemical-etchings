import csv
from typing import List


# Positions of id, name, d2_class, exotic, slot, mob, res, rec, dis, int, str in the CSV Row
CSV_ROW_DEFN = [2, 0, 7, 4, 5, 27, 28, 29, 30, 31, 32]


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


armor_list: List[Armor] = []

with open("armor.csv") as csvfile:
    reader = csv.reader(csvfile, delimiter=",")
    for idx, row in enumerate(reader):
        if idx == 0:
            continue
        armor_list.append(Armor.from_csv_row(row))


delete_list = []
for idx, armor in enumerate(armor_list):
    if armor.is_exotic == True:
        delete_list.append(idx)
for idx in reversed(delete_list):
    armor_list.pop(idx)

delete_list = []
for idx, armor in enumerate(armor_list):
    if armor.slot == "Warlock Bond":
        delete_list.append(idx)
for idx in reversed(delete_list):
    armor_list.pop(idx)

for armor in armor_list:
    for armor2 in armor_list:
        if (
            armor.slot == armor2.slot
            and armor < armor2
            and armor.d2_class == armor2.d2_class
            and (
                (armor.is_exotic and armor2.is_exotic and armor.name == armor2.name)
                or (not armor.is_exotic and not armor2.is_exotic)
            )
        ):
            print("id:", armor.id, " or", sep="", end=" ")
