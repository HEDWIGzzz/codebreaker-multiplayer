from datetime import datetime, timezone
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "codebreaker-secret-key"

# threading ใช้งานง่ายสำหรับเครื่องครู/เครือข่ายภายในห้อง
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# รูปแบบ:
# {
#   "กลุ่ม A": {
#       "group_name": "กลุ่ม A",
#       "current_level": 1,
#       "status": "กำลังเล่น",
#       "unlocked_levels": [],
#       "started_at": datetime,
#       "elapsed_seconds": 0
#   }
# }
groups = {}


def utc_now():
    return datetime.now(timezone.utc)


def format_elapsed(seconds):
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def build_leaderboard():
    """สร้างข้อมูลที่ส่งให้หน้า leaderboard และมือถือ"""
    result = []

    for group in groups.values():
        elapsed = group["elapsed_seconds"]

        if group["status"] == "กำลังเล่น" and group["started_at"]:
            elapsed += int((utc_now() - group["started_at"]).total_seconds())

        result.append({
            "group_name": group["group_name"],
            "current_level": group["current_level"],
            "status": group["status"],
            "unlocked_levels": group["unlocked_levels"],
            "elapsed_seconds": elapsed,
            "elapsed_text": format_elapsed(elapsed)
        })

    # เรียงผู้ที่ผ่านด่านมากก่อน แล้วใช้เวลาน้อยกว่าเป็นอันดับสูงกว่า
    return sorted(
        result,
        key=lambda item: (
            -len(item["unlocked_levels"]),
            item["elapsed_seconds"],
            item["group_name"].lower()
        )
    )


def broadcast_leaderboard():
    socketio.emit("leaderboard_update", build_leaderboard())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/leaderboard")
@app.route("/admin")
def leaderboard():
    return render_template("leaderboard.html")


@socketio.on("join_game")
def join_game(data):
    group_name = str(data.get("group_name", "")).strip()

    if not group_name:
        emit("join_error", {"message": "กรุณากรอกชื่อกลุ่ม"})
        return

    if len(group_name) > 30:
        emit("join_error", {"message": "ชื่อกลุ่มต้องไม่เกิน 30 ตัวอักษร"})
        return

    # ถ้าใช้ชื่อเดิม ให้กลับเข้าสู่ข้อมูลกลุ่มเดิม
    if group_name not in groups:
        groups[group_name] = {
            "group_name": group_name,
            "current_level": 1,
            "status": "กำลังเล่น",
            "unlocked_levels": [],
            "started_at": utc_now(),
            "elapsed_seconds": 0
        }

    emit("join_success", {
        "group_name": group_name,
        "group": groups[group_name]
    })

    broadcast_leaderboard()


@socketio.on("request_leaderboard")
def request_leaderboard():
    emit("leaderboard_update", build_leaderboard())


@socketio.on("unlock_level")
def unlock_level(data):
    """
    เรียก event นี้หลังตรวจคำตอบของด่านในเกมว่าถูกต้องแล้วเท่านั้น
    data ตัวอย่าง:
    {
      "group_name": "Math Masters",
      "level": 2,
      "is_finished": false
    }
    """
    group_name = str(data.get("group_name", "")).strip()
    level = int(data.get("level", 1))
    is_finished = bool(data.get("is_finished", False))

    if group_name not in groups:
        emit("join_error", {"message": "ไม่พบข้อมูลกลุ่ม กรุณาเข้าร่วมเกมใหม่"})
        return

    group = groups[group_name]

    # ป้องกันการนับด่านเดิมซ้ำ
    if level not in group["unlocked_levels"]:
        group["unlocked_levels"].append(level)
        group["unlocked_levels"].sort()

    # ด่านถัดไป
    group["current_level"] = level + 1

    if is_finished:
        if group["started_at"]:
            group["elapsed_seconds"] += int(
                (utc_now() - group["started_at"]).total_seconds()
            )
        group["started_at"] = None
        group["status"] = "ผ่านครบทุกด่าน"
    else:
        group["status"] = f"ปลดล็อกด่าน {level} สำเร็จ"

    emit("unlock_success", {
        "message": f"ปลดล็อกด่าน {level} สำเร็จ",
        "group": group
    })

    # ส่งอัปเดตไปยังจอครูและผู้เล่นทุกคนทันที
    broadcast_leaderboard()


@socketio.on("update_playing_status")
def update_playing_status(data):
    """ใช้เมื่อกลุ่มเริ่มเล่นด่านใหม่"""
    group_name = str(data.get("group_name", "")).strip()
    level = int(data.get("level", 1))

    if group_name not in groups:
        return

    groups[group_name]["current_level"] = level
    groups[group_name]["status"] = "กำลังเล่น"
    broadcast_leaderboard()


if __name__ == "__main__":
    # ใช้ host 0.0.0.0 เพื่อให้นักเรียนเปิดผ่าน IP เครื่องครูใน Wi-Fi เดียวกันได้
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
