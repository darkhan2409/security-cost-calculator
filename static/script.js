// Глобальные переменные
let postCounter = 0;
let tmcItems = [];

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    loadTMC();
    addPost(); // Добавляем первый пост по умолчанию
});

// Переключение вкладок
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
    
    if (tabName === 'tmc') {
        loadTMCList();
    } else {
        loadTMC();
    }
}

// Добавление поста
function addPost() {
    postCounter++;
    const container = document.getElementById('posts-container');
    
    const postCard = document.createElement('div');
    postCard.className = 'post-card';
    postCard.id = `post-${postCounter}`;
    postCard.dataset.postId = postCounter;
    
    postCard.innerHTML = `
        <div class="post-header">
            <h3 class="post-title">Пост №${postCounter}</h3>
            <button class="btn btn-danger" onclick="removePost(${postCounter})">🗑️ Удалить</button>
        </div>
        
        <div class="form-grid">
            <div class="form-group">
                <label>Часов в день:</label>
                <input type="number" id="hours-${postCounter}" min="1" max="24" value="12">
            </div>
            <div class="form-group">
                <label>Дней в неделю:</label>
                <input type="number" id="days-${postCounter}" min="1" max="7" value="7">
            </div>
        </div>
        
        <h4>Персонал:</h4>
        <div id="staff-${postCounter}"></div>
        <button class="btn btn-secondary" onclick="addStaff(${postCounter})">➕ Добавить группу персонала</button>
    `;
    
    container.appendChild(postCard);
    addStaff(postCounter); // Добавляем первую группу персонала
}

// Удаление поста
function removePost(postId) {
    const post = document.getElementById(`post-${postId}`);
    if (post) {
        post.remove();
        renumberPosts(); // Перенумеровываем посты после удаления
    }
}

// Перенумерация постов
function renumberPosts() {
    const postElements = document.querySelectorAll('.post-card');
    postElements.forEach((postEl, index) => {
        const newNumber = index + 1;
        const titleElement = postEl.querySelector('.post-title');
        if (titleElement) {
            titleElement.textContent = `Пост №${newNumber}`;
        }
    });
}

// Добавление группы персонала
let staffCounter = {};
function addStaff(postId) {
    if (!staffCounter[postId]) {
        staffCounter[postId] = 0;
    }
    staffCounter[postId]++;
    
    const container = document.getElementById(`staff-${postId}`);
    const staffId = `staff-${postId}-${staffCounter[postId]}`;
    
    const staffGroup = document.createElement('div');
    staffGroup.className = 'staff-group';
    staffGroup.id = staffId;
    
    staffGroup.innerHTML = `
        <div class="form-grid">
            <div class="form-group">
                <label>Должность:</label>
                <input type="text" id="${staffId}-position" placeholder="Охранник дневной">
            </div>
            <div class="form-group">
                <label>Количество:</label>
                <input type="number" id="${staffId}-count" min="1" value="1">
            </div>
            <div class="form-group">
                <label>ЗП на руки (₸):</label>
                <input type="number" id="${staffId}-salary" min="0" placeholder="150000">
            </div>
            <div class="form-group">
                <button class="btn btn-danger" onclick="removeStaff('${staffId}')">🗑️</button>
            </div>
        </div>
    `;
    
    container.appendChild(staffGroup);
}

// Удаление группы персонала
function removeStaff(staffId) {
    const staff = document.getElementById(staffId);
    if (staff) {
        staff.remove();
    }
}

// Загрузка ТМЦ для выбора
async function loadTMC() {
    try {
        const response = await fetch('/api/tmc');
        tmcItems = await response.json();
        
        const container = document.getElementById('tmc-selection');
        container.innerHTML = '';
        
        if (tmcItems.length === 0) {
            container.innerHTML = '<p>ТМЦ не найдены. Добавьте их во вкладке "Управление ТМЦ".</p>';
            return;
        }
        
        tmcItems.forEach(item => {
            const checkbox = document.createElement('div');
            checkbox.className = 'tmc-checkbox';
            checkbox.innerHTML = `
                <input type="checkbox" id="tmc-check-${item.id}" value="${item.id}">
                <label for="tmc-check-${item.id}">
                    <strong>${item.name}</strong> - ${item.price.toLocaleString()} ₸
                    (амортизация: ${item.amortization_months} мес, ${item.monthly_cost.toLocaleString()} ₸/мес)
                </label>
                <input type="number" id="tmc-qty-${item.id}" min="1" value="1" placeholder="Кол-во">
            `;
            container.appendChild(checkbox);
        });
    } catch (error) {
        console.error('Ошибка загрузки ТМЦ:', error);
    }
}

// Расчет стоимости
async function calculate() {
    try {
        // Собираем данные по постам
        const posts = [];
        const postElements = document.querySelectorAll('.post-card');
        
        postElements.forEach((postEl, index) => {
            const postId = postEl.id.split('-')[1];
            const hours = parseInt(document.getElementById(`hours-${postId}`).value);
            const days = parseInt(document.getElementById(`days-${postId}`).value);
            
            // Собираем персонал
            const staff = [];
            const staffElements = postEl.querySelectorAll('.staff-group');
            
            staffElements.forEach(staffEl => {
                const staffId = staffEl.id;
                const position = document.getElementById(`${staffId}-position`).value;
                const count = parseInt(document.getElementById(`${staffId}-count`).value);
                const salary = parseFloat(document.getElementById(`${staffId}-salary`).value);
                
                if (position && count && salary) {
                    staff.push({ position, count, net_salary: salary });
                }
            });
            
            if (staff.length > 0) {
                posts.push({
                    post_number: index + 1, // Используем индекс для правильной нумерации
                    hours_per_day: hours,
                    days_per_week: days,
                    staff
                });
            }
        });
        
        if (posts.length === 0) {
            alert('Добавьте хотя бы один пост с персоналом');
            return;
        }
        
        // Собираем ТМЦ
        const tmc_items = [];
        tmcItems.forEach(item => {
            const checkbox = document.getElementById(`tmc-check-${item.id}`);
            if (checkbox && checkbox.checked) {
                const quantity = parseInt(document.getElementById(`tmc-qty-${item.id}`).value) || 1;
                tmc_items.push({ item_id: item.id, quantity });
            }
        });
        
        // Маржа
        const markup_percent = parseFloat(document.getElementById('markup').value) || 20;
        
        // Отправляем запрос
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ posts, tmc_items, markup_percent })
        });
        
        if (!response.ok) {
            throw new Error('Ошибка расчета');
        }
        
        const result = await response.json();
        displayResult(result);
        
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при расчете: ' + error.message);
    }
}

// Отображение результата
function displayResult(result) {
    const resultDiv = document.getElementById('result');
    resultDiv.classList.remove('hidden');
    
    let html = '<h2>💰 Результат расчета</h2>';
    
    // Посты
    html += '<div class="result-section"><h3>📍 Посты</h3>';
    result.posts.forEach(post => {
        html += `
            <div style="margin-bottom: 15px;">
                <strong>Пост №${post.post_number}</strong> - График ${post.schedule} (${post.monthly_hours} ч/мес)<br>
        `;
        post.staff_details.forEach(staff => {
            html += `
                &nbsp;&nbsp;• ${staff.position}: ${staff.count} чел. × ${staff.net_salary.toLocaleString()} ₸ = 
                ${staff.total_cost_group.toLocaleString()} ₸/мес<br>
            `;
        });
        html += `<strong>Стоимость поста: ${post.total_labor_cost.toLocaleString()} ₸/мес</strong></div>`;
    });
    html += '</div>';
    
    // ТМЦ
    if (result.tmc.length > 0) {
        html += '<div class="result-section"><h3>📦 ТМЦ</h3>';
        result.tmc.forEach(item => {
            html += `
                <div class="result-row">
                    <span>${item.name} × ${item.quantity} шт</span>
                    <span>${item.monthly_cost.toLocaleString()} ₸/мес</span>
                </div>
            `;
        });
        html += '</div>';
    }
    
    // Итого
    html += `
        <div class="result-section">
            <h3>💵 Итого</h3>
            <div class="result-row">
                <span>ФОТ охраны:</span>
                <span>${result.summary.total_labor_cost.toLocaleString()} ₸/мес</span>
            </div>
            <div class="result-row">
                <span>ТМЦ (амортизация):</span>
                <span>${result.summary.total_tmc_cost.toLocaleString()} ₸/мес</span>
            </div>
            <div class="result-row">
                <span>Себестоимость:</span>
                <span>${result.summary.subtotal.toLocaleString()} ₸/мес</span>
            </div>
            <div class="result-row">
                <span>Маржа (${result.summary.markup_percent}%):</span>
                <span>${result.summary.markup_amount.toLocaleString()} ₸/мес</span>
            </div>
            <div class="result-row total">
                <span>СТОИМОСТЬ УСЛУГИ:</span>
                <span>${result.summary.final_price.toLocaleString()} ₸/мес</span>
            </div>
            <div class="result-row total">
                <span>Тариф за час:</span>
                <span>${result.summary.hourly_rate.toLocaleString()} ₸/ч</span>
            </div>
            <div class="result-row">
                <span>Всего постов:</span>
                <span>${result.summary.total_posts}</span>
            </div>
            <div class="result-row">
                <span>Всего часов в месяц:</span>
                <span>${result.summary.total_monthly_hours} ч</span>
            </div>
        </div>
    `;
    
    resultDiv.innerHTML = html;
    resultDiv.scrollIntoView({ behavior: 'smooth' });
}

// Управление ТМЦ
async function loadTMCList() {
    try {
        const response = await fetch('/api/tmc');
        const items = await response.json();
        
        const container = document.getElementById('tmc-list');
        container.innerHTML = '';
        
        if (items.length === 0) {
            container.innerHTML = '<p>ТМЦ не найдены.</p>';
            return;
        }
        
        items.forEach(item => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'tmc-item';
            itemDiv.innerHTML = `
                <div class="tmc-item-info">
                    <h4>${item.name}</h4>
                    <p>Цена: ${item.price.toLocaleString()} ₸ | Количество: ${item.quantity} шт | 
                    Амортизация: ${item.amortization_months} мес | В месяц: ${item.monthly_cost.toLocaleString()} ₸</p>
                </div>
                <button class="btn btn-danger" onclick="deleteTMC(${item.id})">🗑️ Удалить</button>
            `;
            container.appendChild(itemDiv);
        });
    } catch (error) {
        console.error('Ошибка загрузки ТМЦ:', error);
    }
}

async function addTMC() {
    const name = document.getElementById('tmc-name').value;
    const price = parseFloat(document.getElementById('tmc-price').value);
    const quantity = parseInt(document.getElementById('tmc-quantity').value);
    const amortization = parseInt(document.getElementById('tmc-amortization').value);
    
    if (!name || !price || !quantity || !amortization) {
        alert('Заполните все поля');
        return;
    }
    
    try {
        const response = await fetch('/api/tmc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, price, quantity, amortization_months: amortization })
        });
        
        if (!response.ok) {
            throw new Error('Ошибка добавления ТМЦ');
        }
        
        // Очищаем форму
        document.getElementById('tmc-name').value = '';
        document.getElementById('tmc-price').value = '';
        document.getElementById('tmc-quantity').value = '1';
        document.getElementById('tmc-amortization').value = '';
        
        // Обновляем список
        loadTMCList();
        alert('ТМЦ добавлен');
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при добавлении ТМЦ');
    }
}

async function deleteTMC(id) {
    if (!confirm('Удалить этот ТМЦ?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tmc/${id}`, { method: 'DELETE' });
        
        if (!response.ok) {
            throw new Error('Ошибка удаления ТМЦ');
        }
        
        loadTMCList();
        alert('ТМЦ удален');
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при удалении ТМЦ');
    }
}
