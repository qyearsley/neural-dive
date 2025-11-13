"""Answer matching system for short-answer questions.

Provides flexible matching for typed answers, handling variations in formatting,
spacing, capitalization, and common synonyms.
"""

from __future__ import annotations

import re


def normalize_answer(answer: str) -> str:
    """Normalize an answer for comparison.

    Args:
        answer: Raw answer string

    Returns:
        Normalized lowercase string with extra whitespace removed

    Example:
        >>> normalize_answer("  O(N)  ")
        'o(n)'
        >>> normalize_answer("O( n )")
        'o(n)'
    """
    # Convert to lowercase
    answer = answer.lower().strip()

    # Remove extra spaces inside parentheses and around operators
    answer = re.sub(r"\s+", "", answer)

    return answer


def extract_big_o(answer: str) -> str | None:
    """
    Extract Big-O notation from an answer.

    Args:
        answer: Answer that may contain Big-O notation

    Returns:
        Extracted Big-O (e.g., "n", "logn", "nlogn") or None

    Example:
        >>> extract_big_o("O(n)")
        'n'
        >>> extract_big_o("O(log n)")
        'logn'
        >>> extract_big_o("linear")
        None
    """
    # Match O(...) or o(...)
    match = re.search(r"o\s*\(\s*([^)]+)\s*\)", answer.lower())
    if match:
        complexity = match.group(1).replace(" ", "").replace("*", "")
        return complexity
    return None


# Common synonyms for algorithm complexities.
COMPLEXITY_SYNONYMS = {
    "constant": ["1", "o(1)", "constanttime"],
    "linear": ["n", "o(n)", "lineartime"],
    "logarithmic": ["logn", "o(logn)", "log(n)", "logarithmictime"],
    "linearithmic": ["nlogn", "o(nlogn)", "nlog(n)", "o(nlog(n))"],
    "quadratic": ["n2", "n^2", "o(n2)", "o(n^2)", "quadratictime"],
    "cubic": ["n3", "n^3", "o(n3)", "o(n^3)", "cubictime"],
    "exponential": ["2n", "2^n", "o(2n)", "o(2^n)", "exponentialtime"],
}


def matches_complexity(user_answer: str, correct_answer: str) -> bool:
    """Check if user's answer matches the correct complexity.

    Handles various formats and synonyms for Big-O notation.

    Args:
        user_answer: User's typed answer
        correct_answer: Correct answer(s), can include synonyms separated by |

    Returns:
        True if answers match

    Example:
        >>> matches_complexity("O(n)", "O(n)|linear")
        True
        >>> matches_complexity("linear", "O(n)|linear")
        True
        >>> matches_complexity("O( N )", "O(n)")
        True
        >>> matches_complexity("O(log n)", "O(logn)|logarithmic")
        True
    """
    user_normalized = normalize_answer(user_answer)
    user_big_o = extract_big_o(user_answer)

    # Check against all acceptable answers
    acceptable_answers = [a.strip() for a in correct_answer.split("|")]

    for acceptable in acceptable_answers:
        acceptable_normalized = normalize_answer(acceptable)
        acceptable_big_o = extract_big_o(acceptable)

        # Direct match
        if user_normalized == acceptable_normalized:
            return True

        # Big-O extraction match
        if user_big_o and acceptable_big_o and user_big_o == acceptable_big_o:
            return True

        # Check complexity synonyms
        for _complexity_name, synonyms in COMPLEXITY_SYNONYMS.items():
            if acceptable_normalized in synonyms:
                # Check if user answer is also a synonym
                if user_normalized in synonyms:
                    return True
                # Check if user's Big-O matches
                if user_big_o in synonyms:
                    return True

    return False


def matches_exact(user_answer: str, correct_answer: str, case_sensitive: bool = False) -> bool:
    """Check if user's answer exactly matches (with optional case sensitivity).

    Args:
        user_answer: User's typed answer
        correct_answer: Correct answer(s), can include alternatives separated by |
        case_sensitive: Whether to match case exactly

    Returns:
        True if answers match

    Example:
        >>> matches_exact("DFS", "DFS|Depth-First Search")
        True
        >>> matches_exact("depth-first search", "DFS|Depth-First Search")
        True
        >>> matches_exact("bfs", "BFS", case_sensitive=True)
        False
    """
    # Normalize answers
    user_normalized = user_answer.strip() if case_sensitive else user_answer.lower().strip()

    # Check against all acceptable answers
    acceptable_answers = [a.strip() for a in correct_answer.split("|")]

    for acceptable in acceptable_answers:
        acceptable_normalized = acceptable if case_sensitive else acceptable.lower()

        if user_normalized == acceptable_normalized:
            return True

    return False


def matches_numeric(user_answer: str, correct_answer: str, tolerance: float = 0.01) -> bool:
    """Check if user's numeric answer matches within tolerance.

    Args:
        user_answer: User's typed answer
        correct_answer: Correct numeric answer
        tolerance: Acceptable difference (default 1%)

    Returns:
        True if answers match within tolerance

    Example:
        >>> matches_numeric("3.14", "3.14159")
        True
        >>> matches_numeric("100", "99.5")
        True
        >>> matches_numeric("50", "100")
        False
    """
    try:
        user_val = float(user_answer.strip())
        correct_val = float(correct_answer.strip())

        # Check if within tolerance
        diff = abs(user_val - correct_val)
        max_acceptable = abs(correct_val) * tolerance

        return diff <= max_acceptable or diff < 0.001  # Allow tiny differences
    except ValueError:
        return False


def match_answer(
    user_answer: str,
    correct_answer: str,
    match_type: str = "exact",
    case_sensitive: bool = False,
) -> bool:
    """
    Universal answer matching function.

    Args:
        user_answer: User's typed answer
        correct_answer: Correct answer(s), alternatives separated by |
        match_type: Type of matching: "exact", "complexity", "numeric"
        case_sensitive: Whether exact matching should be case-sensitive

    Returns:
        True if user's answer is acceptable

    Example:
        >>> match_answer("O(n)", "O(n)|linear", match_type="complexity")
        True
        >>> match_answer("DFS", "DFS|Depth-First Search", match_type="exact")
        True
        >>> match_answer("3.14", "3.14159", match_type="numeric")
        True
    """
    if match_type == "complexity":
        return matches_complexity(user_answer, correct_answer)
    elif match_type == "numeric":
        return matches_numeric(user_answer, correct_answer)
    else:  # exact
        return matches_exact(user_answer, correct_answer, case_sensitive)
