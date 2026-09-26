from dataclasses import dataclass


# --------------------------------
# TRADITIONAL CLASS
# --------------------------------

class Student:

    def __init__(
        self,
        name: str,
        age: int,
        department: str
    ):
        self.name = name
        self.age = age
        self.department = department

    def display(self) -> None:
        print("Name:", self.name)
        print("Age:", self.age)
        print("Department:", self.department)


# --------------------------------
# DATACLASS
# --------------------------------

@dataclass
class StudentData:

    name: str
    age: int
    department: str


# --------------------------------
# CREATE OBJECTS
# --------------------------------

student1 = Student(
    "Murari",
    21,
    "Computer Science"
)

student2 = StudentData(
    "Hema",
    21,
    "Computer Science"
)


# --------------------------------
# DISPLAY
# --------------------------------

print("----- TRADITIONAL CLASS -----")

student1.display()


print("\n----- DATACLASS -----")

print("Name:", student2.name)
print("Age:", student2.age)
print("Department:", student2.department)


# --------------------------------
# COMPARISON
# --------------------------------

print("\n----- COMPARISON -----")

print("Traditional class requires manual __init__().")
print("Dataclass automatically generates __init__().")
print("Dataclass requires less boilerplate code.")