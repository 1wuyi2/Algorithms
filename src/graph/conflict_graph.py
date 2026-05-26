"""Conflict graph construction.

Each course is a graph node. An undirected edge is added when two courses
conflict according to the course conflict checker.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, Iterable, Mapping, Optional, Tuple

from src.constraints import ConflictReason, find_course_conflicts
from src.models import Course


@dataclass(frozen=True)
class ConflictEdge:
    """An undirected conflict edge between two courses."""

    course_a_id: str
    course_b_id: str
    reasons: Tuple[ConflictReason, ...]

    def __post_init__(self) -> None:
        if not self.course_a_id or not self.course_b_id:
            raise ValueError("ConflictEdge course ids cannot be empty")
        if self.course_a_id == self.course_b_id:
            raise ValueError("ConflictEdge cannot connect a course to itself")

    def connects(self, course_id: str) -> bool:
        """Return whether this edge touches the given course."""

        return course_id in (self.course_a_id, self.course_b_id)

    def other(self, course_id: str) -> str:
        """Return the opposite endpoint of this edge."""

        if course_id == self.course_a_id:
            return self.course_b_id
        if course_id == self.course_b_id:
            return self.course_a_id
        raise ValueError("course_id is not part of this edge")


@dataclass(frozen=True)
class ConflictGraph:
    """Adjacency-list conflict graph."""

    adjacency: Mapping[str, Tuple[str, ...]]
    edges: Tuple[ConflictEdge, ...]

    @property
    def node_ids(self) -> Tuple[str, ...]:
        """Return all course ids in stable order."""

        return tuple(self.adjacency.keys())

    def neighbors(self, course_id: str) -> Tuple[str, ...]:
        """Return course ids adjacent to the given course."""

        if course_id not in self.adjacency:
            raise KeyError(f"Unknown course id: {course_id}")
        return self.adjacency[course_id]

    def degree(self, course_id: str) -> int:
        """Return the conflict degree of the given course."""

        return len(self.neighbors(course_id))

    def edge_between(self, course_a_id: str, course_b_id: str) -> Optional[ConflictEdge]:
        """Return the conflict edge between two courses if it exists."""

        endpoints = {course_a_id, course_b_id}
        for edge in self.edges:
            if {edge.course_a_id, edge.course_b_id} == endpoints:
                return edge
        return None

    def to_adjacency_dict(self) -> Dict[str, Tuple[str, ...]]:
        """Return a plain dict copy for algorithms or API responses."""

        return {course_id: neighbors for course_id, neighbors in self.adjacency.items()}


def build_conflict_graph(courses: Iterable[Course]) -> ConflictGraph:
    """Build an undirected conflict graph from courses."""

    course_list = tuple(courses)
    course_ids = [course.id for course in course_list]
    if len(course_ids) != len(set(course_ids)):
        raise ValueError("Course ids must be unique to build a conflict graph")

    adjacency_sets = {course.id: set() for course in course_list}
    edges = []

    for course_a, course_b in combinations(course_list, 2):
        result = find_course_conflicts(course_a, course_b)
        if not result.has_conflict:
            continue

        adjacency_sets[course_a.id].add(course_b.id)
        adjacency_sets[course_b.id].add(course_a.id)
        edges.append(
            ConflictEdge(
                course_a_id=course_a.id,
                course_b_id=course_b.id,
                reasons=result.reasons,
            )
        )

    adjacency = {
        course.id: tuple(sorted(adjacency_sets[course.id]))
        for course in course_list
    }
    return ConflictGraph(adjacency=adjacency, edges=tuple(edges))
