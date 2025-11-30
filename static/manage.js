document.addEventListener('DOMContentLoaded', () => {
    // --- 身份验证检查 ---
    if (!localStorage.getItem('app_config_key')) {
        window.location.href = '/login';
        return;
    }

    // --- 状态缓存 ---
    let allTasks = [];
    let allAssets = [];
    let allPrompts = [];

    // --- DOM 元素 ---
    const tableBody = document.getElementById('tasks-table-body');
    const addTaskBtn = document.getElementById('add-task-btn');
    const taskModal = document.getElementById('task-modal');
    const closeModalBtn = taskModal.querySelector('.close-button');
    const taskForm = document.getElementById('task-form');
    const modalTitle = document.getElementById('modal-title');
    const taskIdInput = document.getElementById('task-id');
    const assetSelect = document.getElementById('task-asset');
    const promptSelect = document.getElementById('task-prompt');
    const cycleSelect = document.getElementById('task-cycle');
    const cronInput = document.getElementById('task-cron');
    const activeSelect = document.getElementById('task-active');
    const statusMessage = document.getElementById('task-status-message');

    // --- API 调用函数 ---

    async function fetchData(url, errorMessage) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(errorMessage);
            return await response.json();
        } catch (error) {
            console.error(error);
            alert(error.message);
            return [];
        }
    }

    async function fetchAllData() {
        [allTasks, allAssets, allPrompts] = await Promise.all([
            fetchData('/api/tasks', '获取任务列表失败'),
            fetchData('/api/assets', '获取资产列表失败'),
            fetchData('/api/prompts', '获取提示词列表失败')
        ]);
        renderTable();
        populateSelects();
    }

    // --- 渲染函数 ---

    function renderTable() {
        tableBody.innerHTML = '';
        if (allTasks.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7">未找到任何定时任务。</td></tr>';
            return;
        }

        allTasks.forEach(task => {
            const asset = allAssets.find(a => a.id === task.asset_id) || { symbol: '未知' };
            const prompt = allPrompts.find(p => p.id === task.prompt_id) || { name: '未知', version: '' };
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${task.id}</td>
                <td>${asset.symbol}</td>
                <td>${task.cycle}</td>
                <td>${prompt.name} (v${prompt.version})</td>
                <td><code>${task.cron_expression}</code></td>
                <td><span class="status ${task.is_active ? 'active' : ''}">${task.is_active ? '激活' : '禁用'}</span></td>
                <td>
                    <button class="edit-task-btn" data-id="${task.id}">编辑</button>
                    <button class="delete-task-btn" data-id="${task.id}">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    function populateSelects() {
        assetSelect.innerHTML = allAssets.map(a => `<option value="${a.id}">${a.symbol}</option>`).join('');
        promptSelect.innerHTML = allPrompts.map(p => `<option value="${p.id}">${p.name} (v${p.version})</option>`).join('');
    }

    // --- 模态框控制 ---

    function openModal(task = null) {
        taskForm.reset();
        statusMessage.textContent = '';
        if (task) {
            modalTitle.textContent = '编辑任务';
            taskIdInput.value = task.id;
            assetSelect.value = task.asset_id;
            promptSelect.value = task.prompt_id;
            cycleSelect.value = task.cycle;
            cronInput.value = task.cron_expression;
            activeSelect.value = String(task.is_active);
        } else {
            modalTitle.textContent = '添加新任务';
            taskIdInput.value = '';
        }
        taskModal.style.display = 'block';
    }

    function closeModal() {
        taskModal.style.display = 'none';
    }

    // --- 事件监听器 ---

    addTaskBtn.addEventListener('click', () => openModal());
    closeModalBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (event) => {
        if (event.target === taskModal) closeModal();
    });

    taskForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const id = taskIdInput.value;
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/tasks/${id}` : '/api/tasks';

        const body = {
            asset_id: parseInt(assetSelect.value),
            prompt_id: parseInt(promptSelect.value),
            cycle: cycleSelect.value,
            cron_expression: cronInput.value.trim(),
            is_active: activeSelect.value === 'true'
        };

        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '保存任务失败');
            }
            statusMessage.textContent = '保存成功！';
            statusMessage.style.color = 'green';
            await fetchAllData();
            setTimeout(closeModal, 1000);
        } catch (error) {
            statusMessage.textContent = `错误: ${error.message}`;
            statusMessage.style.color = 'red';
        }
    });

    tableBody.addEventListener('click', async (event) => {
        const target = event.target;
        const taskId = target.dataset.id;

        if (target.classList.contains('edit-task-btn')) {
            const task = allTasks.find(t => t.id == taskId);
            if (task) openModal(task);
        }

        if (target.classList.contains('delete-task-btn')) {
            if (!confirm(`确定要删除任务 ID: ${taskId} 吗?`)) return;
            try {
                const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '删除任务失败');
                }
                await fetchAllData();
            } catch (error) {
                alert(`删除错误: ${error.message}`);
            }
        }
    });

    // --- 初始化 ---
    fetchAllData();
});