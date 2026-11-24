import datetime
import json
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
JSON_PATH = "problems.json"
DUGGA1_PATH = "dugga1.json"
DUGGA2_PATH = "dugga2.json"
TEST_RESULTS_PATH = "test_results.json"

MODULE_NAMES = {
    "l1": "Lektion 1",
    "l1m": "Lektion 1M",
    "l2": "Lektion 2",
    "l2m": "Lektion 2M",
    "l3": "Lektion 3",
    "l3m": "Lektion 3M",
    "l4": "Lektion 4",
    "l4m": "Lektion 4M",
    "l5": "Lektion 5",
    "l5m": "Lektion 5M",
    "l6": "Lektion 6",
    "l6m": "Lektion 6M",
    "h6": "Handledning 6",
    "ha1": "Handledning 1",
}


def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_dugga_source(dugga_id):
    d1 = load_json_file(DUGGA1_PATH)
    if dugga_id in d1:
        return DUGGA1_PATH, d1
    d2 = load_json_file(DUGGA2_PATH)
    if dugga_id in d2:
        return DUGGA2_PATH, d2
    return None, {}


def get_display_name(key):
    return MODULE_NAMES.get(key.lower(), key.upper())


@app.context_processor
def inject_helpers():
    return dict(get_display_name=get_display_name)


def calculate_advanced_stats(data, current_date_str):
    today = datetime.date.fromisoformat(current_date_str)
    total_problems = 0
    completed_problems = 0
    date_counts = {}

    # 1. Samla in totaler och datum per avklarad uppgift
    for module_id, problems in data.items():
        if not isinstance(problems, dict):
            continue
        for prob_id, p_info in problems.items():
            if not isinstance(p_info, dict):
                continue
            total_problems += 1
            if p_info.get("completed"):
                completed_problems += 1
                c_date = p_info.get("completed_date")
                if c_date:
                    date_counts[c_date] = date_counts.get(c_date, 0) + 1

    total_pct = round((completed_problems / total_problems) * 100) if total_problems > 0 else 0
    completed_today = date_counts.get(current_date_str, 0)

    # Beräkna streak (antal dagar i rad med minst 1 avklarad uppgift)
    streak = 0
    check_day = today
    if date_counts.get(check_day.isoformat(), 0) == 0:
        check_day = today - datetime.timedelta(days=1)

    while date_counts.get(check_day.isoformat(), 0) > 0:
        streak += 1
        check_day -= datetime.timedelta(days=1)

    MONTHS_SV = [
        "", "januari", "februari", "mars", "april", "maj", "juni",
        "juli", "augusti", "september", "oktober", "november", "december"
    ]

    def format_sv_date(d):
        suffix = "a" if d.day in (1, 2, 21, 22, 31) else "e"
        return f"{d.day}{suffix} {MONTHS_SV[d.month]}"

    # 2. 28 dagars Heatmap Data
    heatmap_days = []
    for i in range(27, -1, -1):
        d = today - datetime.timedelta(days=i)
        d_str = d.isoformat()
        count = date_counts.get(d_str, 0)

        level = 0
        if count >= 6:
            level = 3
        elif count >= 3:
            level = 2
        elif count >= 1:
            level = 1

        heatmap_days.append({
            "date": d_str,
            "date_label": format_sv_date(d),
            "count": count,
            "level": level,
        })

    # 3. Senaste 7 dagarnas stapeldiagram
    weekly_bars = []
    max_daily = 1
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        d_str = d.isoformat()
        count = date_counts.get(d_str, 0)
        if count > max_daily:
            max_daily = count
        weekly_bars.append({
            "day_name": ["Må", "Ti", "On", "To", "Fr", "Lö", "Sö"][d.weekday()],
            "date_label": format_sv_date(d),
            "count": count,
        })

    for bar in weekly_bars:
        bar["height_pct"] = round((bar["count"] / max_daily) * 100) if max_daily > 0 else 0

    return {
        "total_problems": total_problems,
        "completed_problems": completed_problems,
        "total_pct": total_pct,
        "completed_today": completed_today,
        "streak": streak,
        "heatmap_days": heatmap_days,
        "weekly_bars": weekly_bars,
    }


@app.route("/")
def index():
    data = load_json_file(JSON_PATH)
    del_1 = data.get("del-1", {})
    current_date = datetime.date.today().isoformat()
    stats = calculate_advanced_stats(del_1, current_date)
    return render_template("index.html", modules=del_1, stats=stats)


@app.route("/stats")
def stats():
    del_1 = load_json_file(JSON_PATH).get("del-1", {})
    d1 = load_json_file(DUGGA1_PATH)
    d2 = load_json_file(DUGGA2_PATH)

    combined = dict(del_1)
    for d_id, d_val in {**d1, **d2}.items():
        combined[d_id] = d_val.get("problems", {})

    current_date = datetime.date.today().isoformat()
    adv_stats = calculate_advanced_stats(combined, current_date)

    raw_results = load_json_file(TEST_RESULTS_PATH)
    test_history = raw_results if isinstance(raw_results, list) else []

    return render_template("stats.html", adv_stats=adv_stats, test_history=test_history)


@app.route("/duggor/<dugga_id>/test/save_result", methods=["POST"])
def save_dugga_test_result(dugga_id):
    payload = request.get_json(silent=True) or {}
    _, data = get_dugga_source(dugga_id)
    if dugga_id not in data:
        return {"status": "error"}, 404

    dugga_title = data[dugga_id]["title"]
    prefix = "Dugga 1" if dugga_id.startswith("dugga-1") else "Dugga 2"

    raw = load_json_file(TEST_RESULTS_PATH)
    history = raw if isinstance(raw, list) else []

    entry = {
        "id": payload.get("result_id"),
        "dugga_id": dugga_id,
        "title": f"{prefix} – {dugga_title}",
        "date": datetime.date.today().isoformat(),
        "duration_seconds": payload.get("duration_seconds", 0),
        "duration_formatted": payload.get("duration_formatted", "00:00"),
        "score": payload.get("score", 0),
        "total": payload.get("total", 0),
        "correct_probs": payload.get("correct_probs", []),
        "wrong_probs": payload.get("wrong_probs", []),
    }

    # Uppdatera befintlig post om användaren justerar självrättningen på samma inlämning
    existing_idx = next((i for i, item in enumerate(history) if item.get("id") == entry["id"]), None)
    if existing_idx is not None:
        history[existing_idx] = entry
    else:
        history.insert(0, entry)

    save_json_file(TEST_RESULTS_PATH, history)
    return {"status": "ok"}


@app.route("/duggor")
def duggor():
    d1 = load_json_file(DUGGA1_PATH)
    d2 = load_json_file(DUGGA2_PATH)
    current_date = datetime.date.today().isoformat()

    all_dugga_modules = {k: v.get("problems", {}) for k, v in {**d1, **d2}.items()}
    dugga_stats = calculate_advanced_stats(all_dugga_modules, current_date)
    return render_template("duggor.html", dugga1=d1, dugga2=d2, stats=dugga_stats)


@app.route("/duggor/<dugga_id>")
def view_dugga(dugga_id):
    _, data = get_dugga_source(dugga_id)
    if dugga_id not in data:
        return redirect(url_for("duggor"))
    return render_template("dugga_module.html", dugga_id=dugga_id, dugga=data[dugga_id])


@app.route("/duggor/<dugga_id>/prob/<prob_id>")
def view_dugga_problem(dugga_id, prob_id):
    _, data = get_dugga_source(dugga_id)
    if dugga_id not in data or prob_id not in data[dugga_id]["problems"]:
        return redirect(url_for("duggor"))

    dugga = data[dugga_id]
    prob_data = dugga["problems"][prob_id]
    keys = list(dugga["problems"].keys())
    idx = keys.index(prob_id)

    prev_prob = keys[idx - 1] if idx > 0 else None
    next_prob = keys[idx + 1] if idx < len(keys) - 1 else None

    return render_template(
        "dugga_problem.html",
        dugga_id=dugga_id,
        dugga_title=dugga["title"],
        selected_prob=prob_id,
        prob_data=prob_data,
        prev_prob=prev_prob,
        next_prob=next_prob,
    )


@app.route("/duggor/toggle", methods=["POST"])
def toggle_dugga_prob():
    dugga_id = request.form.get("dugga_id")
    prob = request.form.get("prob")

    path, data = get_dugga_source(dugga_id)
    if path and prob in data[dugga_id]["problems"]:
        current = data[dugga_id]["problems"][prob].get("completed", False)
        new_status = not current
        data[dugga_id]["problems"][prob]["completed"] = new_status

        if new_status:
            data[dugga_id]["problems"][prob]["completed_date"] = datetime.date.today().isoformat()
        else:
            data[dugga_id]["problems"][prob].pop("completed_date", None)

        save_json_file(path, data)

    return redirect(url_for("view_dugga_problem", dugga_id=dugga_id, prob_id=prob))


@app.route("/duggor/bookmark", methods=["POST"])
def bookmark_dugga_prob():
    dugga_id = request.form.get("dugga_id")
    prob = request.form.get("prob")

    path, data = get_dugga_source(dugga_id)
    if path and prob in data[dugga_id]["problems"]:
        current = data[dugga_id]["problems"][prob].get("bookmarked", False)
        data[dugga_id]["problems"][prob]["bookmarked"] = not current
        save_json_file(path, data)

    return redirect(url_for("view_dugga_problem", dugga_id=dugga_id, prob_id=prob))

@app.route("/duggor/<dugga_id>/test")
def dugga_test(dugga_id):
    _, data = get_dugga_source(dugga_id)
    if dugga_id not in data:
        return redirect(url_for("duggor"))
    return render_template("dugga_test.html", dugga_id=dugga_id, dugga=data[dugga_id])


@app.route("/duggor/<dugga_id>/test/sync", methods=["POST"])
def sync_dugga_test(dugga_id):
    payload = request.get_json(silent=True) or {}
    completed_ids = payload.get("completed_ids", [])

    path, data = get_dugga_source(dugga_id)
    if path and dugga_id in data:
        today_str = datetime.date.today().isoformat()
        for prob_id in completed_ids:
            if prob_id in data[dugga_id]["problems"]:
                data[dugga_id]["problems"][prob_id]["completed"] = True
                data[dugga_id]["problems"][prob_id]["completed_date"] = today_str
        save_json_file(path, data)
        return {"status": "ok"}

    return {"status": "error"}, 400


@app.route("/bookmarks")
def bookmarks():
    del_1 = load_json_file(JSON_PATH).get("del-1", {})
    d1 = load_json_file(DUGGA1_PATH)
    d2 = load_json_file(DUGGA2_PATH)
    bookmarked_items = []

    for mod_name, probs in del_1.items():
        for prob_key, prob_info in probs.items():
            if prob_info.get("bookmarked"):
                bookmarked_items.append({
                    "title": f"[{get_display_name(mod_name)}] Uppgift {prob_key}",
                    "url": url_for("view_problem", module_name=mod_name, prob_id=prob_key),
                    "completed": prob_info.get("completed", False),
                })

    for prefix, d_dict in [("Dugga 1", d1), ("Dugga 2", d2)]:
        for dugga_id, dugga in d_dict.items():
            for prob_key, prob_info in dugga.get("problems", {}).items():
                if prob_info.get("bookmarked"):
                    bookmarked_items.append({
                        "title": f"[{prefix} – {dugga['title']}] Uppgift {prob_key}",
                        "url": url_for("view_dugga_problem", dugga_id=dugga_id, prob_id=prob_key),
                        "completed": prob_info.get("completed", False),
                    })

    return render_template("bookmarks.html", bookmarked_items=bookmarked_items)


@app.route("/module/<module_name>")
def view_module(module_name):
    data = load_json_file(JSON_PATH)
    del_1 = data.get("del-1", {})
    if module_name not in del_1:
        return redirect(url_for("index"))
    return render_template("module.html", current_module=module_name, probs=del_1[module_name])


@app.route("/module/<module_name>/prob/<prob_id>")
def view_problem(module_name, prob_id):
    data = load_json_file(JSON_PATH)
    del_1 = data.get("del-1", {})
    if module_name not in del_1 or prob_id not in del_1[module_name]:
        return redirect(url_for("index"))

    prob_data = del_1[module_name][prob_id]
    keys = list(del_1[module_name].keys())
    idx = keys.index(prob_id)

    prev_prob = keys[idx - 1] if idx > 0 else None
    next_prob = keys[idx + 1] if idx < len(keys) - 1 else None

    return render_template(
        "problem.html",
        current_module=module_name,
        selected_prob=prob_id,
        prob_data=prob_data,
        prev_prob=prev_prob,
        next_prob=next_prob,
    )


@app.route("/toggle", methods=["POST"])
def toggle():
    module = request.form.get("module")
    prob = request.form.get("prob")

    data = load_json_file(JSON_PATH)
    if module in data.get("del-1", {}) and prob in data["del-1"][module]:
        current_status = data["del-1"][module][prob]["completed"]
        new_status = not current_status
        data["del-1"][module][prob]["completed"] = new_status

        if new_status:
            data["del-1"][module][prob]["completed_date"] = datetime.date.today().isoformat()
        else:
            data["del-1"][module][prob].pop("completed_date", None)

        save_json_file(JSON_PATH, data)

    return redirect(url_for("view_problem", module_name=module, prob_id=prob))


@app.route("/toggle_bookmark", methods=["POST"])
def toggle_bookmark():
    module = request.form.get("module")
    prob = request.form.get("prob")

    data = load_json_file(JSON_PATH)
    if module in data.get("del-1", {}) and prob in data["del-1"][module]:
        current_status = data["del-1"][module][prob].get("bookmarked", False)
        data["del-1"][module][prob]["bookmarked"] = not current_status
        save_json_file(JSON_PATH, data)

    return redirect(url_for("view_problem", module_name=module, prob_id=prob))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
