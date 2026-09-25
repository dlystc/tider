from typing import TypeVar, Generic, Hashable, Dict, List, Set

T = TypeVar("T", bound=Hashable)


class DSU(Generic[T]):
    def __init__(self) -> None:
        self.parent: Dict[T, T] = {}
        self.rank: Dict[T, int] = {}

    def add(self, x: T) -> None:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x: T) -> T:
        self.add(x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # 路径压缩
        return self.parent[x]

    def union(self, x: T, y: T) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True

    def connected(self, x: T, y: T) -> bool:
        return self.find(x) == self.find(y)

    def groups(self) -> List[Set[T]]:
        res: Dict[T, Set[T]] = {}
        for x in self.parent:
            root = self.find(x)
            res.setdefault(root, set()).add(x)
        return list(res.values())