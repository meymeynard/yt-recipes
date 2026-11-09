import re
from typing import List, Dict, Optional, Tuple

# Comprehensive Ingredient Alias Mapping
INGREDIENT_ALIASES: Dict[str, List[str]] = {
    # Proteins
    "chicken breast": ["chicken breast", "chicken fillet", "chicken breast fillet", "boneless chicken", "chicken breast strips"],
    "chicken": ["chicken", "manok", "chicken thigh", "chicken drumstick", "chicken wings"],
    "ground pork": ["ground pork", "lean ground pork", "minced pork", "pork giniling", "giniling na baboy", "giniling"],
    "pork": ["pork", "pork belly", "liempo", "kasim", "baboy", "pork shoulder", "pork chops"],
    "ground beef": ["ground beef", "minced beef", "beef giniling"],
    "beef": ["beef", "beef sirloin", "beef flank", "baka"],
    "egg": ["egg", "eggs", "itlog", "beaten egg", "scrambled egg"],
    "salted egg": ["salted egg", "salted duck egg", "itlog na maalat", "itlog na pula"],
    "shrimp": ["shrimp", "shrimps", "hipon", "prawns"],
    "tofu": ["tofu", "tokwa", "firm tofu"],

    # Vegetables
    "ampalaya": ["ampalaya", "bitter melon", "bitter gourd", "bitter squash"],
    "okra": ["okra", "lady finger", "lady's finger", "ladies fingers"],
    "sayote": ["sayote", "chayote", "chayote squash"],
    "carrots": ["carrot", "carrots"],
    "green peas": ["green peas", "peas", "frozen peas", "guisantes"],
    "chickpeas": ["garbanzos", "garbanzo", "chickpeas", "chickpea", "garbanzo beans"],
    "corn": ["whole corn", "corn kernels", "sweet corn", "corn", "whole kernel corn", "canned corn"],
    "red bell pepper": ["red bell pepper", "red pepper", "bell pepper", "bell peppers", "capsicum"],
    "green bell pepper": ["green bell pepper"],
    "chili": ["green chili", "green chilies", "red chili", "siling labuyo", "sili", "jalapeno", "chilies"],
    "mushroom": ["mushroom", "mushrooms", "mushroom stems", "shiitake", "button mushroom", "oyster mushroom"],
    "tomato": ["tomato", "tomatoes", "kamatis", "roma tomato"],
    "potato": ["potato", "potatoes", "patatas"],
    "cabbage": ["cabbage", "repolyo"],
    "eggplant": ["eggplant", "talong", "aubergine"],
    "sitaw": ["string beans", "sitaw", "yardlong beans", "green beans"],
    "kangkong": ["kangkong", "water spinach", "river spinach"],
    "spinach": ["spinach"],
    "bok choy": ["bok choy", "pechay", "pak choi"],

    # Aromatics & Herbs
    "garlic": ["garlic", "bawang", "minced garlic", "garlic cloves", "crushed garlic"],
    "red onion": ["red onion", "red onions", "shallot", "shallots", "sibuyas tagalog"],
    "white onion": ["white onion", "yellow onion", "onion", "onions", "sweet onion", "sibuyas"],
    "ginger": ["ginger", "luya", "fresh ginger", "sliced ginger", "minced ginger"],
    "scallions": ["scallions", "green onion", "spring onion", "chives", "onion leeks", "leeks"],

    # Citrus
    "calamansi": ["calamansi", "kalamansi", "calamondin"],
    "lemon": ["lemon", "lemon juice", "fresh lemon"],
    "lime": ["lime", "lime juice"],

    # Sauces, Condiments & Seasonings
    "oyster sauce": ["oyster sauce", "oyster flavored sauce"],
    "soy sauce": ["soy sauce", "toyo", "light soy sauce", "dark soy sauce", "tamari"],
    "fish sauce": ["fish sauce", "patis"],
    "vinegar": ["vinegar", "suka", "cane vinegar", "white vinegar", "apple cider vinegar"],
    "sesame oil": ["sesame oil"],
    "cooking oil": ["cooking oil", "vegetable oil", "canola oil", "olive oil", "oil for cooking"],
    "black pepper": ["black pepper", "ground black pepper", "paminta", "cracked black pepper", "peppercorns"],
    "salt": ["salt", "asin", "sea salt", "kosher salt", "fine salt"],
    "sugar": ["sugar", "brown sugar", "white sugar", "granulated sugar"],
    "cornstarch": ["cornstarch", "corn starch", "flour"],
    "tomato sauce": ["tomato sauce", "tomato paste"],
    "chicken broth": ["chicken broth", "chicken stock", "vegetable broth", "water or chicken broth", "chicken bouillon", "chicken cube"],
}

# Regex to pinpoint the ingredients section (only match true ingredient headers)
START_MARKERS = [
    r'^\s*ingredients\s*[:\-]?',
    r'^\s*mga\s+sangkap\s*[:\-]?',
    r'^\s*sangkap\s*[:\-]?',
    r'^\s*what\s+you[\'\s]*ll\s+need\s*[:\-]?',
    r'^\s*recipe\s+ingredients\s*[:\-]?',
]

END_MARKERS = [
    r'^\s*instructions\b',
    r'^\s*procedure\b',
    r'^\s*paraan\b',
    r'^\s*directions\b',
    r'^\s*method\b',
    r'^\s*preparation\b',
    r'^\s*how\s+to\s+cook\b',
    r'^\s*steps\b',
    r'^\s*timestamps\b',
    r'^\s*connect\s+with\b',
    r'^\s*subscribe\b',
    r'^\s*follow\s+us\b',
    r'^\s*social\s+media\b'
]

START_REGEX = re.compile(r'(' + '|'.join(START_MARKERS) + r')', re.IGNORECASE | re.MULTILINE)
END_REGEX = re.compile(r'(' + '|'.join(END_MARKERS) + r')', re.IGNORECASE | re.MULTILINE)

def extract_ingredients_section(description: str) -> str:
    """Extracts the raw text chunk containing ingredients from the video description."""
    if not description:
        return ""

    start_match = START_REGEX.search(description)
    if not start_match:
        return description

    start_pos = start_match.end()
    sub_text = description[start_pos:]

    end_match = END_REGEX.search(sub_text)
    if end_match:
        extracted = sub_text[:end_match.start()].strip()
        if len(extracted) > 10:
            return extracted
            
    return sub_text.strip()

def match_line_to_ingredients(line: str) -> List[str]:
    """Given a single line from an ingredient list, identify which canonical ingredients it mentions."""
    clean_line = " " + line.lower().strip() + " "
    matched = []
    
    # Sort aliases by descending length so "chicken breast" matches before "chicken", "salted egg" before "egg"
    sorted_canonical = sorted(
        INGREDIENT_ALIASES.keys(),
        key=lambda k: max(len(alias) for alias in INGREDIENT_ALIASES[k]),
        reverse=True
    )

    for canonical in sorted_canonical:
        aliases = INGREDIENT_ALIASES[canonical]
        for alias in aliases:
            pattern = r'(?:\b|_)' + re.escape(alias) + r'(?:\b|_)'
            if re.search(pattern, clean_line):
                matched.append(canonical)
                clean_line = re.sub(pattern, " [MATCHED] ", clean_line)
                break

    return matched

def parse_recipe_description(title: str, description: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Parses a video description and title into:
    - raw_ingredients_text (the extracted block)
    - list of dicts: [{"name": canonical_name, "raw_line": original_line}]
    """
    section = extract_ingredients_section(description)
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    
    results: List[Dict[str, str]] = []
    found_names = set()

    for line in lines:
        if line.startswith("http") or len(line) < 3 or set(line).issubset({'-', '=', '*', '#', ' '}):
            continue
            
        matched_canonicals = match_line_to_ingredients(line)
        for name in matched_canonicals:
            if name not in found_names:
                found_names.add(name)
                results.append({
                    "name": name,
                    "raw_line": line
                })

    # Also scan title for core proteins / main ingredients
    title_matches = match_line_to_ingredients(title)
    for name in title_matches:
        if name not in found_names:
            found_names.add(name)
            results.append({
                "name": name,
                "raw_line": f"[From Title] {title}"
            })

    return section, results
