const SERVER_URL = 'http://localhost:5001';

async function updateUI() {
    try {
        const response = await fetch(`${SERVER_URL}/status`);
        const data = await response.json();
        
        if (data.weather) {
            document.getElementById('temp-val').innerText = data.weather.temp.toFixed(1);
            document.getElementById('hum-val').innerText = data.weather.hum.toFixed(0);
        }

        let freeCount = 0;
        data.slots.forEach(slot => {
            const card = document.getElementById(`slot-${slot.id}`);
            const badge = document.getElementById(`badge-${slot.id}`);
            const btn = document.getElementById(`btn-${slot.id}`);

            if (!card) return;

            if (slot.status === 1) {
                card.className = 'parking-card occupied';
                badge.innerText = 'Зайнято';
                btn.innerText = 'Місце зайняте';
                btn.disabled = true;
            } else if (slot.is_reserved) {
                card.className = 'parking-card reserved';
                badge.innerText = 'Заброньовано';
                btn.innerText = 'Скасувати';
                btn.disabled = false;
                freeCount++;
            } else {
                card.className = 'parking-card free';
                badge.innerText = 'Вільно';
                btn.innerText = 'Забронювати';
                btn.disabled = false;
                freeCount++;
            }
        });
        document.getElementById('free-count').innerText = freeCount;

        const statsBody = document.getElementById('stats-body');
        if (statsBody) {
            statsBody.innerHTML = ''; 
            data.history.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.time}</td>
                    <td>${row.free}</td>
                    <td>${row.temp}°C</td>
                    <td>${row.hum}%</td>
                    <td>
                        <button onclick="deleteLog(${row.id})" style="background:none; border:none; color:#ef4444; cursor:pointer; font-weight:bold; font-size: 1.2rem;">✕</button>
                    </td>
                `;
                statsBody.appendChild(tr);
            });
        }

    } catch (e) {
        console.error("Помилка завантаження даних:", e);
    }
}

async function deleteLog(id) {
    if (!confirm(`Видалити запис?`)) return;

    try {
        const response = await fetch(`${SERVER_URL}/logs/delete/${id}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.status === "success") {
            updateUI();
        } else {
            alert("Помилка: " + result.message);
        }
    } catch (e) {
        console.error("Помилка при видаленні запису:", e);
    }
}

async function toggleReservation(id) {
    try {
        const response = await fetch(`${SERVER_URL}/reserve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({id: id})
        });
        
        if (response.ok) {
            updateUI();
        } else {
            const err = await response.json();
            alert(err.message);
        }
    } catch (e) { 
        console.error("Помилка бронювання:", e); 
    }
}

async function clearHistory() {
    if (!confirm("Ви впевнені, що хочете повністю очистити ВСІ дані статистики та логів?")) return;

    try {
        const response = await fetch(`${SERVER_URL}/logs/clear`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (result.status === "success") {
            alert(result.message);
            updateUI();
        }
    } catch (e) {
        console.error("Помилка при очищенні:", e);
    }
}

setInterval(updateUI, 2000);
updateUI();