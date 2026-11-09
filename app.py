import streamlit as st
import db
import parser
import matcher
import youtube_client
import ingest

st.set_page_config(
    page_title="Pantry Chef | YouTube Recipe Aggregator",
    page_icon="🍳",
    layout="wide"
)

# Initialize database
db.init_db()

# Custom Styling
st.markdown("""
<style>
    .metric-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-green { background-color: #d1fae5; color: #065f46; border: 1px solid #34d399; }
    .badge-yellow { background-color: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
    .badge-gray { background-color: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
    .badge-missing { background-color: #fee2e2; color: #991b1b; border: 1px solid #f87171; }
    .recipe-card {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 20px;
        background: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR: INVENTORY & SYNC ----------------- #
with st.sidebar:
    st.title("🍳 Pantry Inventory")
    
    # Presets
    user_initial_basket = [
        "ampalaya", "carrots", "okra", "calamansi", "green peas",
        "chickpeas", "corn", "sayote", "chicken breast", "egg",
        "salted egg", "ground pork", "red bell pepper", "lemon",
        "mushroom", "red onion", "white onion", "garlic", "ginger",
        "oyster sauce", "soy sauce"
    ]

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📋 Load My Basket", use_container_width=True):
            st.session_state["pantry"] = list(user_initial_basket)
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state["pantry"] = []
            st.rerun()

    if "pantry" not in st.session_state:
        st.session_state["pantry"] = list(user_initial_basket)

    # Organized ingredient categories
    CATEGORIES = {
        "🥩 Proteins": ["chicken breast", "chicken", "ground pork", "pork", "egg", "salted egg", "ground beef", "beef", "shrimp", "tofu"],
        "🥦 Vegetables": ["ampalaya", "okra", "sayote", "carrots", "green peas", "chickpeas", "corn", "red bell pepper", "mushroom", "tomato", "potato", "cabbage", "eggplant", "sitaw", "kangkong", "bok choy"],
        "🧄 Aromatics & Citrus": ["garlic", "white onion", "red onion", "ginger", "calamansi", "lemon", "scallions"],
        "🧂 Sauces & Seasonings": ["soy sauce", "oyster sauce", "fish sauce", "vinegar", "sesame oil", "cooking oil", "salt", "black pepper", "sugar", "cornstarch", "tomato sauce"]
    }

    selected_pantry = set(st.session_state["pantry"])

    for cat_name, items in CATEGORIES.items():
        with st.expander(cat_name, expanded=(cat_name in ["🥩 Proteins", "🥦 Vegetables"])):
            for item in items:
                checked = item in selected_pantry
                new_state = st.checkbox(item.title(), value=checked, key=f"ing_{item}")
                if new_state and item not in selected_pantry:
                    selected_pantry.add(item)
                elif not new_state and item in selected_pantry:
                    selected_pantry.remove(item)

    st.session_state["pantry"] = list(selected_pantry)

    st.divider()
    st.subheader("⚙️ Channel Sync")
    channel_to_sync = st.text_input("Channel Name / Handle", value="Panlasang Pinoy")
    fetch_limit = st.slider("Videos to fetch", min_value=10, max_value=60, value=30, step=10)
    
    if st.button("📥 Sync Channel to Database", use_container_width=True):
        with st.spinner(f"Fetching upload playlist for '{channel_to_sync}'..."):
            count = ingest.ingest_channel(channel_to_sync, max_videos=fetch_limit)
            st.success(f"Synced {count} videos into SQLite!")
            st.rerun()

    stats = db.get_stats()
    st.caption(f"📊 Indexed Recipes: **{stats['recipes']}** | Unique Ingredients: **{stats['ingredients']}**")


# ----------------- MAIN VIEW ----------------- #
st.title("🍳 What Can I Cook Today?")
st.write(f"You have **{len(st.session_state['pantry'])} ingredients** selected in your pantry.")

# Display Pantry Chips
if st.session_state["pantry"]:
    chips_html = "".join([f'<span class="metric-badge badge-green" style="margin: 2px;">✓ {item}</span>' for item in sorted(st.session_state["pantry"])])
    st.markdown(f"<div>{chips_html}</div>", unsafe_allow_html=True)
else:
    st.info("Your pantry is empty! Select ingredients in the sidebar or click 'Load My Basket'.")

st.write("")

# Tabs: Indexed Recipes vs Live Search
tab_matched, tab_search = st.tabs(["✨ Matched Recipes", "🔍 Live YouTube Search"])

with tab_matched:
    # Controls
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    with col_f1:
        min_match = st.slider("Min Match %", min_value=10, max_value=100, value=30, step=10)
    with col_f2:
        max_missing = st.slider("Max Missing Ingredients", min_value=0, max_value=10, value=4)
    with col_f3:
        assume_staples = st.checkbox("Assume basic staples (oil, salt, pepper, water)", value=True)

    recipes = db.get_all_recipes_with_ingredients()
    
    if not recipes:
        st.warning("No recipes in local database yet! Click 'Sync Channel to Database' in the sidebar to populate your favorite channels.")
    else:
        results = matcher.rank_recipes(
            recipes=recipes,
            user_pantry=set(st.session_state["pantry"]),
            min_match_pct=min_match,
            max_missing=max_missing,
            assume_staples=assume_staples
        )

        st.subheader(f"Found {len(results)} Matching Recipes")

        for r in results:
            with st.container():
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    st.image(r["thumbnail_url"], use_container_width=True)
                with col_info:
                    # Match score badge
                    badge_class = "badge-green" if r["match_percentage"] >= 80 else ("badge-yellow" if r["match_percentage"] >= 50 else "badge-gray")
                    cookable_tag = " <span class='metric-badge badge-green'>🎉 Ready to Cook!</span>" if r["is_cookable"] else ""
                    
                    st.markdown(f"### [{r['title']}](https://www.youtube.com/watch?v={r['video_id']})")
                    st.markdown(f"""
                        <span class="metric-badge {badge_class}">{r['match_percentage']}% Match</span>
                        <span class="metric-badge badge-gray">{r['channel_name']}</span>
                        {cookable_tag}
                    """, unsafe_allow_html=True)
                    
                    st.write("")
                    
                    # Ingredients have vs missing
                    matched_html = " ".join([f"<span class='metric-badge badge-green'>✓ {i}</span>" for i in r["matched"]])
                    missing_html = " ".join([f"<span class='metric-badge badge-missing'>✗ {i}</span>" for i in r["missing"]])
                    
                    if matched_html:
                        st.markdown(f"**In your pantry:** {matched_html}", unsafe_allow_html=True)
                    if missing_html:
                        st.markdown(f"**Missing:** {missing_html}", unsafe_allow_html=True)

                    with st.expander("📖 View Recipe Ingredients & Instructions"):
                        st.text(r["raw_ingredients_text"] if r["raw_ingredients_text"] else r["description"][:1000])
                        st.link_button("▶️ Watch Video on YouTube", f"https://www.youtube.com/watch?v={r['video_id']}")

                st.divider()

with tab_search:
    st.subheader("Query YouTube Data API On-Demand")
    st.caption("Search for any specific recipe or ingredient combo and import it directly into your database.")
    
    search_q = st.text_input("Search query", value="Chicken Sayote")
    if st.button("Search YouTube"):
        with st.spinner("Searching YouTube API and parsing descriptions..."):
            live_results = youtube_client.search_youtube_recipes(search_q, max_results=8)
            st.success(f"Found {len(live_results)} videos from YouTube!")
            
            for item in live_results:
                raw_text, parsed_ings = parser.parse_recipe_description(item["title"], item["description"])
                col_s1, col_s2 = st.columns([1, 2])
                with col_s1:
                    st.image(item["thumbnail_url"], use_container_width=True)
                with col_s2:
                    st.markdown(f"#### [{item['title']}](https://www.youtube.com/watch?v={item['video_id']})")
                    st.caption(f"Channel: {item['channel_name']}")
                    ing_names = [i["name"] for i in parsed_ings]
                    st.write(f"**Parsed Ingredients ({len(ing_names)}):** {', '.join(ing_names) if ing_names else 'None detected'}")
                    
                    if st.button("💾 Save to Database", key=f"save_{item['video_id']}"):
                        db.save_recipe(
                            video_id=item["video_id"],
                            title=item["title"],
                            channel_name=item["channel_name"],
                            channel_id=item["channel_id"],
                            published_at=item["published_at"],
                            thumbnail_url=item["thumbnail_url"],
                            description=item["description"],
                            raw_ingredients_text=raw_text,
                            ingredients=parsed_ings
                        )
                        st.success("Saved to database!")
                        st.rerun()
                st.divider()
