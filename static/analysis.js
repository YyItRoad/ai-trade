document.addEventListener('DOMContentLoaded', () => {
    // --- 身份验证检查 ---
    if (!localStorage.getItem('app_config_key')) {
        window.location.href = '/login';
        return;
    }

    const tableBody = document.getElementById('analysis-table-body');
    const paginationContainer = document.querySelector('.pagination');
    let currentPage = 1;
    const pageSize = 20;

    async function fetchAnalysisHistory(page = 1) {
        try {
            const response = await fetch(`/api/analysis?page=${page}&page_size=${pageSize}`);
            if (!response.ok) {
                throw new Error('获取分析历史失败');
            }
            const result = await response.json();
            renderTable(result.data);
            renderPagination(result.total_pages, page);
            currentPage = page;
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="7" class="error">加载历史记录出错: ${error.message}</td></tr>`;
        }
    }

    function renderTable(data) {
        tableBody.innerHTML = '';
        if (!data || data.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7">未找到任何分析记录。</td></tr>';
            return;
        }

        data.forEach(record => {
            const row = document.createElement('tr');
            const timestamp = new Date(record.timestamp).toLocaleString();
            row.innerHTML = `
                <td>${record.id}</td>
                <td>${record.asset}</td>
                <td>${record.cycle}</td>
                <td>${timestamp}</td>
                <td>${record.trend || 'N/A'}</td>
                <td>${record.confidence !== null ? record.confidence.toFixed(2) : 'N/A'}</td>
                <td>${record.conclusion || 'N/A'}</td>
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
            if (i === activePage) {
                pageLink.classList.add('active');
            }
            pageLink.addEventListener('click', (e) => {
                e.preventDefault();
                fetchAnalysisHistory(i);
            });
            paginationContainer.appendChild(pageLink);
        }
    }

    // --- 初始化 ---
    fetchAnalysisHistory(currentPage);
});