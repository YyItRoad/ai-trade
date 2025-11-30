document.addEventListener('DOMContentLoaded', () => {
    // --- 身份验证检查 ---
    if (!localStorage.getItem('app_config_key')) {
        window.location.href = '/login';
        return;
    }

    // --- 状态与DOM ---
    const tableBody = document.getElementById('plans-table-body');
    const paginationContainer = document.querySelector('.pagination');
    const statusModal = document.getElementById('status-modal');
    const closeModalBtn = statusModal.querySelector('.close-button');
    const statusForm = document.getElementById('status-form');
    const planIdDisplay = document.getElementById('plan-id-display');
    const planIdInput = document.getElementById('plan-id-input');
    const statusSelect = document.getElementById('plan-status-select');
    const statusMessage = document.getElementById('status-message');

    let currentPage = 1;
    const pageSize = 20;
    let dictionary = {};

    // --- API 调用 ---

    async function fetchDictionary() {
        try {
            const response = await fetch('/api/dictionary');
            if (!response.ok) throw new Error('获取字典数据失败');
            const data = await response.json();
            // 将字典数据处理成更易于查询的格式
            data.forEach(item => {
                if (!dictionary[item.category]) {
                    dictionary[item.category] = {};
                }
                dictionary[item.category][item.code] = item.label;
            });
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    }

    async function fetchPlans(page = 1) {
        try {
            const response = await fetch(`/api/plans?page=${page}&page_size=${pageSize}`);
            if (!response.ok) throw new Error('获取交易计划失败');
            const result = await response.json();
            renderTable(result.data);
            renderPagination(result.total_pages, page);
            currentPage = page;
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="10" class="error">加载交易计划出错: ${error.message}</td></tr>`;
        }
    }

    // --- 渲染函数 ---

    function renderTable(data) {
        tableBody.innerHTML = '';
        if (!data || data.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="10">未找到任何交易计划。</td></tr>';
            return;
        }

        const directionMap = dictionary['direction'] || {};
        const statusMap = dictionary['trade_plan_status'] || {};

        data.forEach(plan => {
            const row = document.createElement('tr');
            const directionText = directionMap[plan.direction] || plan.direction;
            const statusText = statusMap[plan.status] || plan.status;

            row.innerHTML = `
                <td>${plan.id}</td>
                <td>${plan.asset}</td>
                <td>${plan.cycle}</td>
                <td>${directionText}</td>
                <td>${plan.entry_price || 'N/A'}</td>
                <td>${plan.stop_loss || 'N/A'}</td>
                <td>${plan.take_profit_1 || 'N/A'}</td>
                <td>${plan.take_profit_2 || 'N/A'}</td>
                <td><span class="status ${plan.status.toLowerCase()}">${statusText}</span></td>
                <td><button class="edit-status-btn" data-id="${plan.id}">更新状态</button></td>
            `;
            tableBody.appendChild(row);
        });
    }

    function renderPagination(totalPages, activePage) {
        paginationContainer.innerHTML = '';
        if (totalPages <= 1) return;
        for (let i = 1; i <= totalPages; i++) {
            const pageLink = document.createElement('a');
            pageLink.href = '#';
            pageLink.textContent = i;
            if (i === activePage) pageLink.classList.add('active');
            pageLink.addEventListener('click', (e) => {
                e.preventDefault();
                fetchPlans(i);
            });
            paginationContainer.appendChild(pageLink);
        }
    }

    function populateStatusSelect() {
        const statusMap = dictionary['trade_plan_status'] || {};
        statusSelect.innerHTML = Object.entries(statusMap)
            .map(([code, label]) => `<option value="${code}">${label}</option>`)
            .join('');
    }

    // --- 模态框控制 ---

    function openModal(planId) {
        planIdDisplay.textContent = planId;
        planIdInput.value = planId;
        statusMessage.textContent = '';
        statusModal.style.display = 'block';
    }

    function closeModal() {
        statusModal.style.display = 'none';
    }

    // --- 事件监听器 ---

    closeModalBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (event) => {
        if (event.target === statusModal) closeModal();
    });

    tableBody.addEventListener('click', (event) => {
        if (event.target.classList.contains('edit-status-btn')) {
            openModal(event.target.dataset.id);
        }
    });

    statusForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const planId = planIdInput.value;
        const newStatus = statusSelect.value;

        try {
            const response = await fetch(`/api/plans/${planId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '更新状态失败');
            }
            statusMessage.textContent = '更新成功！';
            statusMessage.style.color = 'green';
            await fetchPlans(currentPage);
            setTimeout(closeModal, 1000);
        } catch (error) {
            statusMessage.textContent = `错误: ${error.message}`;
            statusMessage.style.color = 'red';
        }
    });

    // --- 初始化 ---
    async function initialize() {
        await fetchDictionary();
        populateStatusSelect();
        await fetchPlans(currentPage);
    }

    initialize();
});