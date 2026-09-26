from dataclasses import dataclass, field
from typing import Generic, TypeVar, List

T = TypeVar("T")


@dataclass
class Stack(Generic[T]):
    items: List[T] = field(default_factory=list)

    def push(self, item: T) -> None:
        self.items.append(item)

    def pop(self) -> T:
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.items.pop()

    def peek(self) -> T:
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.items[-1]

    def is_empty(self) -> bool:
        return len(self.items) == 0


@dataclass
class Queue(Generic[T]):
    items: List[T] = field(default_factory=list)

    def enqueue(self, item: T) -> None:
        self.items.append(item)

    def dequeue(self) -> T:
        if self.is_empty():
            raise IndexError("Queue is empty")
        return self.items.pop(0)

    def front(self) -> T:
        if self.is_empty():
            raise IndexError("Queue is empty")
        return self.items[0]

    def is_empty(self) -> bool:
        return len(self.items) == 0


# Stack
print("----- STACK -----")

stack = Stack[int]()

stack.push(10)
stack.push(20)
stack.push(30)

print("Stack:", stack.items)
print("Top:", stack.peek())
print("Popped:", stack.pop())
print("Stack after pop:", stack.items)


# Queue
print("\n----- QUEUE -----")

queue = Queue[int]()

queue.enqueue(10)
queue.enqueue(20)
queue.enqueue(30)

print("Queue:", queue.items)
print("Front:", queue.front())
print("Dequeued:", queue.dequeue())
print("Queue after dequeue:", queue.items)