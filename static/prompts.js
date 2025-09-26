document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const tableBody = document.getElementById('prompts-table-body');
    const createPromptBtn = document.getElementById('create-prompt-btn');

    // --- Modal Elements ---
    const modal = document.getElementById('prompt-modal');
    const viewModal = document.getElementById('view-prompt-modal');
    const closeModalBtns = document.querySelectorAll('.close-btn');
    const promptForm = document.getElementById('prompt-form');
    const modalTitle = document.getElementById('modal-title');
    const promptNameInput = document.getElementById('prompt-name');
    const promptContentInput = document.getElementById('prompt-content');
    const viewModalTitle = document.getElementById('view-modal-title');
    const viewPromptContent = document.getElementById('view-prompt-content');
    const copyFromViewBtn = document.getElementById('copy-from-view-btn');

    let allPrompts = []; // Store flattened list of all prompts

    // --- API Functions ---
    const fetchPrompts = async () => {
        try {
            const response = await fetch('/api/prompts');
            if (!response.ok) {
                throw new Error('Failed to fetch prompts');
            }
            const groupedPrompts = await response.json();
            
            // Flatten the grouped prompts into a single list
            allPrompts = Object.values(groupedPrompts).flat().sort((a, b) => b.id - a.id);
            
            renderTable(allPrompts);
        } catch (error) {
            console.error('Error fetching prompts:', error);
            tableBody.innerHTML = `<tr><td colspan="7" class="error">加载提示词失败，请稍后重试。</td></tr>`;
        }
    };

    // --- Render Functions ---
    const renderTable = (prompts) => {
        tableBody.innerHTML = '';
        if (prompts.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center;">还没有任何提示词，请创建一个。</td></tr>`;
            return;
        }

        prompts.forEach(prompt => {
            const row = document.createElement('tr');
            row.className = prompt.is_active ? 'active-row' : '';

            const statusText = prompt.is_active ? '激活中' : '未激活';
            const statusClass = prompt.is_active ? 'status-active' : 'status-inactive';

            row.innerHTML = `
                <td>${prompt.id}</td>
                <td>${prompt.name}</td>
                <td>V${prompt.version}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td class="content-preview">${prompt.content.substring(0, 50)}...</td>
                <td>${new Date(prompt.created_at).toLocaleString()}</td>
                <td class="actions col-actions">
                    <button class="action-btn view-prompt-btn" data-id="${prompt.id}">查看</button>
                    <button class="action-btn activate-prompt-btn" data-id="${prompt.id}" ${prompt.is_active ? 'disabled' : ''}>激活</button>
                    <button class="action-btn delete-prompt-btn" data-id="${prompt.id}" ${prompt.is_active ? 'title="激活中的提示词无法删除"' : ''}>删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    };

    // --- Event Listeners ---
    createPromptBtn.addEventListener('click', () => {
        modalTitle.textContent = '创建新提示词';
        promptForm.reset();
        promptNameInput.disabled = false;
        modal.style.display = 'block';
    });

    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modal.style.display = 'none';
            viewModal.style.display = 'none';
        });
    });

    window.addEventListener('click', (event) => {
        if (event.target == modal || event.target == viewModal) {
            modal.style.display = 'none';
            viewModal.style.display = 'none';
        }
    });

    promptForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const name = promptNameInput.value;
        const content = promptContentInput.value;

        if (!name.trim() || !content.trim()) {
            alert('提示词名称和内容不能为空！');
            return;
        }

        try {
            const response = await fetch('/api/prompts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, content }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to save prompt');
            }
            modal.style.display = 'none';
            fetchPrompts(); // Refresh list
        } catch (error) {
            console.error('Error saving prompt:', error);
            alert(`保存失败: ${error.message}`);
        }
    });

    tableBody.addEventListener('click', async (event) => {
        const target = event.target;
        const id = target.dataset.id;

        if (!id) return;

        // Activate Button
        if (target.classList.contains('activate-prompt-btn')) {
            try {
                const response = await fetch(`/api/prompts/${id}/activate`, { method: 'POST' });
                if (!response.ok) throw new Error('Activation failed');
                fetchPrompts();
            } catch (error) {
                console.error('Error activating prompt:', error);
                alert('激活失败！');
            }
        }

        // View Button
        if (target.classList.contains('view-prompt-btn')) {
            try {
                const res = await fetch(`/api/prompts/${id}`);
                if (!res.ok) throw new Error('Could not fetch prompt details');
                const prompt = await res.json();
                viewModalTitle.textContent = `查看提示词: ${prompt.name} (V${prompt.version})`;
                viewPromptContent.textContent = prompt.content;
                copyFromViewBtn.dataset.id = prompt.id; // 将ID传递给模态框中的复制按钮
                viewModal.style.display = 'block';
            } catch (e) {
                alert('加载完整内容失败！');
            }
        }

        // Delete Button
        if (target.classList.contains('delete-prompt-btn')) {
            const promptToDelete = allPrompts.find(p => p.id == id);
            if (!promptToDelete) return;

            if (promptToDelete.is_active) {
                alert('无法删除一个处于激活状态的提示词。请先激活另一个版本。');
                return;
            }

            if (confirm(`确定要删除提示词 "${promptToDelete.name}" (V${promptToDelete.version}) 吗？\n此操作不可撤销。`)) {
                try {
                    const response = await fetch(`/api/prompts/${id}`, { method: 'DELETE' });
                    
                    if (response.status === 204) { // No Content, success
                        fetchPrompts(); // Refresh list
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || '删除失败');
                    }
                } catch (error) {
                    console.error('Error deleting prompt:', error);
                    alert(`删除失败: ${error.message}`);
                }
            }
        }
    });

    // --- Event listener for the new "Copy" button inside the view modal ---
    copyFromViewBtn.addEventListener('click', async () => {
        const id = copyFromViewBtn.dataset.id;
        if (!id) return;

        try {
            const res = await fetch(`/api/prompts/${id}`);
            if (!res.ok) throw new Error('Could not fetch prompt details');
            const prompt = await res.json();
            
            // Close the view modal
            viewModal.style.display = 'none';

            // Populate and open the edit/create modal
            modalTitle.textContent = `创建新版本 (基于 V${prompt.version})`;
            promptNameInput.value = prompt.name;
            promptNameInput.disabled = true; // Name cannot be changed when creating a new version
            promptContentInput.value = prompt.content;
            modal.style.display = 'block';
        } catch (e) {
            alert('加载内容以复制失败！');
        }
    });

    // --- Initial Load ---
    fetchPrompts();
});