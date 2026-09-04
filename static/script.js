const socket = io();

let currentGroupName = localStorage.getItem("codebreaker_group_name") || "";
let currentLevel = 1;

// DOM ที่ควรมีใน index.html
const joinPanel = document.getElementById("join-panel");
const gamePanel = document.getElementById("game-panel");
const groupNameInput = document.getElementById("group-name");
const joinButton = document.getElementById("join-button");
const groupNameDisplay = document.getElementById("group-name-display");
const joinMessage = document.getElementById("join-message");

function showJoinMessage(message, isError = false) {
    if (!joinMessage) return;

    joinMessage.textContent = message;
    joinMessage.className = isError ? "message error" : "message success";
}

function startGameUI(groupName) {
    if (groupNameDisplay) {
        groupNameDisplay.textContent = groupName;
    }

    if (joinPanel) {
        joinPanel.style.display = "none";
    }

    if (gamePanel) {
        gamePanel.style.display = "block";
    }

    // เรียกฟังก์ชันเดิมของเกมได้ตรงนี้ เช่น loadLevel(currentLevel)
    if (typeof loadLevel === "function") {
        loadLevel(currentLevel);
    }
}

function joinGame() {
    const groupName = groupNameInput.value.trim();

    if (!groupName) {
        showJoinMessage("กรุณากรอกชื่อกลุ่ม", true);
        groupNameInput.focus();
        return;
    }

    socket.emit("join_game", {
        group_name: groupName
    });
}

if (joinButton) {
    joinButton.addEventListener("click", joinGame);
}

if (groupNameInput) {
    groupNameInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            joinGame();
        }
    });
}

socket.on("connect", () => {
    // กลับเข้าห้องด้วยชื่อกลุ่มเดิม หลัง refresh หน้าเว็บ
    if (currentGroupName) {
        socket.emit("join_game", {
            group_name: currentGroupName
        });
    }
});

socket.on("join_success", (data) => {
    currentGroupName = data.group_name;
    currentLevel = data.group.current_level || 1;

    localStorage.setItem("codebreaker_group_name", currentGroupName);
    startGameUI(currentGroupName);
});

socket.on("join_error", (data) => {
    showJoinMessage(data.message, true);
});

socket.on("unlock_success", (data) => {
    console.log(data.message);

    // สามารถเปลี่ยนเป็น Modal / Toast ของโปรเจกต์เดิมได้
    alert(`🎉 ${data.message}`);

    currentLevel = data.group.current_level;

    // โหลดด่านต่อไปในระบบเกมเดิม
    if (typeof loadLevel === "function") {
        loadLevel(currentLevel);
    }
});

/**
 * เรียกหลังตรวจคำตอบถูกแล้ว
 *
 * ตัวอย่าง:
 * if (answerIsCorrect) {
 *   unlockCurrentLevel(currentLevel, currentLevel === TOTAL_LEVELS);
 * }
 */
function unlockCurrentLevel(level, isFinished = false) {
    if (!currentGroupName) {
        alert("กรุณาตั้งชื่อกลุ่มก่อนเริ่มเกม");
        return;
    }

    socket.emit("unlock_level", {
        group_name: currentGroupName,
        level: level,
        is_finished: isFinished
    });
}

/**
 * เรียกเมื่อนักเรียนเริ่มด่านใหม่ หากต้องการให้จอครูเห็นทันที
 */
function reportCurrentLevel(level) {
    if (!currentGroupName) return;

    currentLevel = level;

    socket.emit("update_playing_status", {
        group_name: currentGroupName,
        level: level
    });
}
