from typing import List, Dict, Any, Set

# Basic staples that most people have at home (can be excluded from missing penalties)
DEFAULT_STAPLES = {
    "salt",
    "black pepper",
    "cooking oil",
    "water",
    "sugar"
}

def score_recipe(
    recipe: Dict[str, Any],
    user_pantry: Set[str],
    assume_staples: bool = True
) -> Dict[str, Any]:
    """
    Computes matching statistics for a single recipe against user's pantry.
    """
    recipe_ings = set(recipe.get("ingredients", []))
    
    # If the recipe has no ingredients parsed, score 0
    if not recipe_ings:
        return {
            **recipe,
            "match_percentage": 0,
            "matched": [],
            "missing": [],
            "total_count": 0,
            "is_cookable": False
        }

    # Filter out basic staples if requested
    scoring_ings = recipe_ings
    effective_pantry = set(user_pantry)
    if assume_staples:
        effective_pantry.update(DEFAULT_STAPLES)

    matched = scoring_ings.intersection(effective_pantry)
    missing = scoring_ings - effective_pantry

    # Calculate percentage
    match_pct = round((len(matched) / len(scoring_ings)) * 100) if scoring_ings else 0

    return {
        **recipe,
        "match_percentage": match_pct,
        "matched": sorted(list(matched)),
        "missing": sorted(list(missing)),
        "total_count": len(scoring_ings),
        "is_cookable": len(missing) == 0
    }

def rank_recipes(
    recipes: List[Dict[str, Any]],
    user_pantry: Set[str],
    min_match_pct: int = 20,
    max_missing: int = 5,
    assume_staples: bool = True
) -> List[Dict[str, Any]]:
    """
    Scores and filters recipes according to user's pantry.
    """
    scored = [score_recipe(r, user_pantry, assume_staples) for r in recipes]
    
    # Filter
    filtered = [
        r for r in scored
        if r["match_percentage"] >= min_match_pct and len(r["missing"]) <= max_missing
    ]

    # Sort: Cookable first, then highest match %, then fewest missing items
    filtered.sort(
        key=lambda r: (
            1 if r["is_cookable"] else 0,
            r["match_percentage"],
            -len(r["missing"]),
            len(r["matched"])
        ),
        reverse=True
    )

    return filtered
