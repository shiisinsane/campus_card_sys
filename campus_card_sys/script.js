// 全局变量
let currentUser = null;
const API_BASE = 'http://localhost:5000';

// 连接保持机制
let keepAliveInterval = null;
let connectionStatus = 'connected';

// 页面切换函数
function showPage(pageId) {
    console.log(`页面切换: ${pageId}, 当前用户:`, currentUser ? currentUser.full_name : '未登录');
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(pageId).classList.add('active');
}

function showRegister() {
    showPage('register-page');
}

function showLogin() {
    // 清除可能存在的无效用户状态
    if (currentUser) {
        console.log('强制跳转到登录页面，清除当前用户状态');
        currentUser = null;
        localStorage.removeItem('currentUser');
    }
    showPage('login-page');
}

function showHome() {
    showPage('home-page');
    updateUserInfo();
}

function showReportCard() {
    showPage('report-card-page');
}

function showQueryCard() {
    showPage('query-card-page');
    updateHistoryDisplay(); // 显示查询历史
    document.getElementById('query-student-id').focus(); // 自动聚焦到输入框
}

function showPublicList() {
    showPage('public-list-page');
    loadHotLocations(); // 加载热门地点
    loadPublicList();   // 加载公示列表
}

function showForum() {
    showPage('forum-page');
    loadForumPosts();
}

function showCreatePost() {
    showPage('create-post-page');

    // 设置复选框互斥逻辑
    setTimeout(() => {
        const isAdCheckbox = document.getElementById('is-ad');
        const isAdviceCheckbox = document.getElementById('is-advice');

        if (isAdCheckbox && isAdviceCheckbox) {
            // 移除之前的事件监听器（如果有的话）
            isAdCheckbox.removeEventListener('change', handleAdChange);
            isAdviceCheckbox.removeEventListener('change', handleAdviceChange);

            // 添加新的事件监听器
            isAdCheckbox.addEventListener('change', handleAdChange);
            isAdviceCheckbox.addEventListener('change', handleAdviceChange);
        }
    }, 0);
}

function showRewards() {
    showPage('rewards-page');
    loadRewards();
}

function showSmartLocationQuery() {
    showPage('smart-location-page');
    document.getElementById('location-input').focus(); // 自动聚焦到输入框
}

function logout() {
    currentUser = null;
    // 清除保存的用户状态
    localStorage.removeItem('currentUser');
    showLogin();
}

// 连接保持函数
async function keepAlive() {
    try {
        const response = await fetch(`${API_BASE}/ping`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: 5000
        });

        if (response.ok) {
            connectionStatus = 'connected';
            updateConnectionStatus();
        } else {
            throw new Error('Ping failed');
        }
    } catch (error) {
        console.warn('连接保持失败:', error);
        connectionStatus = 'disconnected';
        updateConnectionStatus();
    }
}

// 更新连接状态显示
function updateConnectionStatus() {
    // 可以在这里添加UI状态指示器
    if (connectionStatus === 'disconnected') {
        console.warn('与服务器连接中断，正在尝试重连...');
    }
}

// 启动连接保持
function startKeepAlive() {
    if (keepAliveInterval) {
        clearInterval(keepAliveInterval);
    }
    // 每30秒ping一次服务器
    keepAliveInterval = setInterval(keepAlive, 30000);
    console.log('连接保持机制已启动');
}

// 停止连接保持
function stopKeepAlive() {
    if (keepAliveInterval) {
        clearInterval(keepAliveInterval);
        keepAliveInterval = null;
        console.log('连接保持机制已停止');
    }
}

// API 调用函数（增强版）
async function apiCall(endpoint, method = 'GET', data = null, retries = 3) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, options);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'API调用失败');
            }

            // 成功时更新连接状态
            connectionStatus = 'connected';
            updateConnectionStatus();

            return result;
        } catch (error) {
            console.error(`API调用错误 (尝试 ${attempt}/${retries}):`, error);

            if (attempt === retries) {
                connectionStatus = 'disconnected';
                updateConnectionStatus();
                alert('操作失败: ' + error.message + '\n请检查网络连接或刷新页面重试');
                throw error;
            }

            // 等待一段时间后重试
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}

// 注册功能
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const studentId = document.getElementById('reg-student-id').value;
    const fullName = document.getElementById('reg-full-name').value;
    const password = document.getElementById('reg-password').value;
    
    try {
        await apiCall('/register', 'POST', {
            student_id: studentId,
            full_name: fullName,
            password: password
        });
        
        alert('注册成功！请登录');
        showLogin();
        
        // 清空表单
        document.getElementById('register-form').reset();
    } catch (error) {
        // 错误已在apiCall中处理
    }
});

// 登录功能
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const studentId = document.getElementById('login-student-id').value;
    const fullName = document.getElementById('login-full-name').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const result = await apiCall('/login', 'POST', {
            student_id: studentId,
            full_name: fullName,
            password: password
        });
        
        currentUser = result;
        // 保存用户状态到localStorage
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        alert('登录成功！');
        showHome();

        // 清空表单
        document.getElementById('login-form').reset();
    } catch (error) {
        // 错误已在apiCall中处理
    }
});

// 更新用户信息显示
function updateUserInfo() {
    if (currentUser) {
        document.getElementById('user-name').textContent = `欢迎，${currentUser.full_name}`;
        document.getElementById('user-points').textContent = `积分：${currentUser.points}`;
        document.getElementById('current-points').textContent = currentUser.points;

        // 确保用户状态同步到localStorage
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
    } else {
        // 如果没有用户信息，清除localStorage
        localStorage.removeItem('currentUser');
    }
}

// 图片预览功能
document.getElementById('photo-upload').addEventListener('change', function(e) {
    const file = e.target.files[0];
    const previewDiv = document.getElementById('photo-preview');

    if (file) {
        // 检查文件类型
        if (!file.type.startsWith('image/')) {
            alert('请选择图片文件');
            e.target.value = '';
            return;
        }

        // 检查文件大小 (16MB)
        if (file.size > 16 * 1024 * 1024) {
            alert('图片文件不能超过16MB');
            e.target.value = '';
            return;
        }

        // 创建预览
        const reader = new FileReader();
        reader.onload = function(e) {
            previewDiv.innerHTML = `
                <img src="${e.target.result}" alt="预览图片">
                <div class="preview-info">文件名: ${file.name} (${(file.size / 1024).toFixed(1)} KB)</div>
                <button type="button" class="remove-photo" onclick="removePhoto()">移除图片</button>
            `;
        };
        reader.readAsDataURL(file);
    } else {
        previewDiv.innerHTML = '';
    }
});

// 移除图片功能
function removePhoto() {
    document.getElementById('photo-upload').value = '';
    document.getElementById('photo-preview').innerHTML = '';
}

// 切换联系方式字段显示
function toggleContactField() {
    const handlerOption = document.querySelector('input[name="handler-option"]:checked');
    const contactField = document.getElementById('contact-field');
    const contactInput = document.getElementById('contact-phone');
    const pickupLocationField = document.getElementById('pickup-location-field');
    const pickupLocationSelect = document.getElementById('pickup-location');

    if (handlerOption && handlerOption.value === '1') {
        // 选择自行联系，显示联系方式字段，隐藏地点选择
        contactField.style.display = 'block';
        pickupLocationField.style.display = 'none';
        contactInput.required = true;
        pickupLocationSelect.required = false;
        pickupLocationSelect.value = '';
        contactInput.focus();
    } else if (handlerOption && handlerOption.value === '2') {
        // 选择放置地点，显示地点选择字段，隐藏联系方式
        contactField.style.display = 'none';
        pickupLocationField.style.display = 'block';
        contactInput.required = false;
        pickupLocationSelect.required = true;
        contactInput.value = '';
        pickupLocationSelect.focus();
    } else {
        // 未选择，隐藏所有字段
        contactField.style.display = 'none';
        pickupLocationField.style.display = 'none';
        contactInput.required = false;
        pickupLocationSelect.required = false;
        contactInput.value = '';
        pickupLocationSelect.value = '';
    }
}

// 报告校园卡功能
document.getElementById('report-card-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // 检查用户是否已登录
    if (!currentUser) {
        alert('请先登录后再提交捡卡信息');
        showLogin();
        return;
    }

    const cardNumber = document.getElementById('card-number').value;
    const foundLocation = document.getElementById('found-location').value;
    const handlerOption = document.querySelector('input[name="handler-option"]:checked').value;
    const contactPhone = document.getElementById('contact-phone').value;
    const pickupLocation = document.getElementById('pickup-location').value;
    const photoFile = document.getElementById('photo-upload').files[0];

    // 验证联系方式
    if (handlerOption === '1' && !contactPhone.trim()) {
        alert('选择"自行联系失主"时必须提供联系方式');
        document.getElementById('contact-phone').focus();
        return;
    }

    // 验证拾取点选择
    if (handlerOption === '2' && !pickupLocation) {
        alert('选择"放置到指定地点"时必须选择拾取点');
        document.getElementById('pickup-location').focus();
        return;
    }

    try {
        // 创建FormData对象来支持文件上传
        const formData = new FormData();
        formData.append('card_number', cardNumber);
        formData.append('found_location', foundLocation);
        formData.append('handler_option', handlerOption);
        // 添加当前登录用户信息用于积分奖励
        formData.append('current_user_id', currentUser.user_id);
        formData.append('current_user_name', currentUser.full_name);

        // 根据处理方式添加相应的contact信息
        if (handlerOption === '1' && contactPhone.trim()) {
            // 自行联系：添加联系方式
            formData.append('contact', contactPhone.trim());
        } else if (handlerOption === '2' && pickupLocation) {
            // 放置指定地点：添加拾取点信息
            formData.append('contact', pickupLocation);
        }

        if (photoFile) {
            formData.append('photo', photoFile);
        }

        // 使用fetch直接发送FormData
        const response = await fetch(`${API_BASE}/report_card`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '提交失败');
        }

        // 如果获得了积分奖励，更新当前用户的积分
        if (result.points_awarded && result.points_awarded > 0) {
            currentUser.points += result.points_awarded;
            // 更新localStorage中的用户信息
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            updateUserInfo(); // 更新界面显示的积分
        }

        alert(result.message);
        document.getElementById('report-card-form').reset();
        document.getElementById('photo-preview').innerHTML = '';
        // 隐藏所有动态字段
        document.getElementById('contact-field').style.display = 'none';
        document.getElementById('pickup-location-field').style.display = 'none';

        // 确保用户仍然登录，然后显示主页
        if (currentUser) {
            showHome();
        } else {
            console.warn('用户状态丢失，重新显示登录页面');
            showLogin();
        }
    } catch (error) {
        console.error('提交错误:', error);
        alert('操作失败: ' + error.message);
    }
});

// 查询历史存储
let queryHistory = JSON.parse(localStorage.getItem('queryHistory') || '[]');

// 显示查询状态
function showQueryStatus(type, message) {
    const statusDiv = document.getElementById('query-status');
    statusDiv.className = `query-status ${type}`;
    statusDiv.textContent = message;

    if (type !== 'loading') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 3000);
    }
}

// 添加查询历史
function addToHistory(studentId, result) {
    const historyItem = {
        studentId: studentId,
        timestamp: new Date().toLocaleString(),
        result: result.status === 'found' ? '找到校园卡' : '未找到校园卡',
        fullResult: result
    };

    // 避免重复添加相同的查询
    queryHistory = queryHistory.filter(item => item.studentId !== studentId);
    queryHistory.unshift(historyItem);

    // 只保留最近10条记录
    if (queryHistory.length > 10) {
        queryHistory = queryHistory.slice(0, 10);
    }

    localStorage.setItem('queryHistory', JSON.stringify(queryHistory));
    updateHistoryDisplay();
}

// 更新历史显示
function updateHistoryDisplay() {
    const historySection = document.getElementById('query-history-section');
    const historyDiv = document.getElementById('query-history');

    if (queryHistory.length > 0) {
        historySection.style.display = 'block';
        historyDiv.innerHTML = '';

        queryHistory.forEach(item => {
            historyDiv.innerHTML += `
                <div class="history-item" onclick="replayQuery('${item.studentId}')">
                    <div class="history-query">学号: ${item.studentId}</div>
                    <div class="history-time">${item.timestamp}</div>
                    <div class="history-result">${item.result}</div>
                </div>
            `;
        });
    } else {
        historySection.style.display = 'none';
    }
}

// 重新执行查询
function replayQuery(studentId) {
    document.getElementById('query-student-id').value = studentId;
    document.getElementById('query-card-form').dispatchEvent(new Event('submit'));
}

// 清空查询
function clearQuery() {
    document.getElementById('query-student-id').value = '';
    document.getElementById('query-result').innerHTML = '';
    document.getElementById('query-status').style.display = 'none';
    document.getElementById('query-student-id').focus();
}

// 清空历史
function clearHistory() {
    if (confirm('确定要清空查询历史吗？')) {
        queryHistory = [];
        localStorage.removeItem('queryHistory');
        updateHistoryDisplay();
    }
}

// 查询校园卡功能
document.getElementById('query-card-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const studentId = document.getElementById('query-student-id').value.trim();

    if (!studentId) {
        showQueryStatus('error', '请输入学号');
        return;
    }

    // 显示加载状态
    showQueryStatus('loading', '正在查询...');

    try {
        const result = await apiCall(`/query_lost_card?student_id=${studentId}`);

        const resultDiv = document.getElementById('query-result');

        if (result.status === 'found') {
            let contactInfoHtml = '';

            if (result.handler_type === 'contact' && result.contact_info) {
                // 自行联系：显示联系方式
                contactInfoHtml = `
                    <div class="contact-info">
                        <div class="contact-label">📞 拾卡者联系方式：</div>
                        <div class="contact-value">${result.contact_info}</div>
                    </div>
                `;
            } else if (result.handler_type === 'location' && result.location_info) {
                // 放置地点：显示地点信息
                contactInfoHtml = `
                    <div class="location-info">
                        <div class="location-label">📍 领取地点：</div>
                        <div class="location-value">${result.location_info}</div>
                    </div>
                `;
            }

            // 检查是否显示删除按钮（只有当前登录用户查询自己的记录时才显示）
            let deleteButtonHtml = '';
            if (currentUser && result.student_id === currentUser.student_id) {
                deleteButtonHtml = `
                    <div class="delete-action">
                        <button class="delete-btn" onclick="deleteCardRecord(${result.card_id}, '${result.student_id}')">
                            🗑️ 删除此记录
                        </button>
                        <small class="delete-hint">删除后此记录将不再显示在公示列表中</small>
                    </div>
                `;
            }

            resultDiv.innerHTML = `
                <div class="result-item">
                    <h4>🎉 好消息！</h4>
                    <p>${result.message}</p>
                    ${contactInfoHtml}
                    ${deleteButtonHtml}
                </div>
            `;
            showQueryStatus('success', '查询成功！找到了您的校园卡');
        } else {
            resultDiv.innerHTML = `
                <div class="result-item">
                    <h4>📋 查询结果</h4>
                    <p>${result.message}</p>
                </div>
            `;

            if (result.unmatched_cards && result.unmatched_cards.length > 0) {
                resultDiv.innerHTML += '<h4>🔍 未匹配的校园卡：</h4>';
                result.unmatched_cards.forEach(card => {
                    // 根据是否有真实姓名显示不同的信息
                    let ownerInfo = '';
                    if (card.owner_name && card.name_source === 'real') {
                        ownerInfo = `<strong>卡主姓名：</strong>${card.owner_name} (${card.masked_info.student_id})`;
                    } else {
                        ownerInfo = `<strong>持卡人信息：</strong>持卡人 (${card.masked_info.student_id})`;
                    }

                    // 检查是否显示删除按钮（只有当前登录用户的记录才显示）
                    let deleteButtonHtml = '';
                    if (currentUser && card.student_id === currentUser.student_id) {
                        deleteButtonHtml = `
                            <div class="delete-action">
                                <button class="delete-btn" onclick="deleteCardRecord(${card.card_id}, '${card.student_id}')">
                                    🗑️ 删除此记录
                                </button>
                                <small class="delete-hint">删除后此记录将不再显示在公示列表中</small>
                            </div>
                        `;
                    }

                    resultDiv.innerHTML += `
                        <div class="result-item">
                            <p><strong>发现时间：</strong>${card.found_time}</p>
                            <p><strong>发现地点：</strong>${card.found_location}</p>
                            <p>${ownerInfo}</p>
                            ${deleteButtonHtml}
                        </div>
                    `;
                });
            }
            showQueryStatus('success', '查询完成');
        }

        // 添加到查询历史
        addToHistory(studentId, result);

        // 滚动到结果区域
        document.getElementById('query-result-section').scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });

    } catch (error) {
        showQueryStatus('error', '查询失败，请稍后重试');
        document.getElementById('query-result').innerHTML = `
            <div class="result-item">
                <h4>❌ 查询失败</h4>
                <p>网络错误或服务器异常，请稍后重试</p>
            </div>
        `;
    }
});

// 全局变量存储图表实例和数据
let locationsChart = null;
let locationsData = [];
let currentChartType = 'grid';

// 加载热门地点
async function loadHotLocations() {
    try {
        const response = await apiCall('/hot_locations');

        // 处理新的响应格式
        let locations, statistics;
        if (response.locations) {
            // 新格式：包含locations数组和statistics对象
            locations = response.locations;
            statistics = response.statistics;
        } else {
            // 兼容旧格式：直接是locations数组
            locations = response;
            statistics = null;
        }

        locationsData = locations; // 保存数据供图表使用

        // 更新卡片视图
        updateGridView(locations, statistics);

        // 如果当前是图表视图，更新图表
        if (currentChartType !== 'grid') {
            updateChart(currentChartType);
        }

    } catch (error) {
        document.getElementById('hot-locations-content').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <div class="empty-text">加载失败</div>
                <div class="empty-hint">请稍后重试</div>
            </div>
        `;
    }
}

// 更新卡片网格视图
function updateGridView(locations, statistics) {
    const contentDiv = document.getElementById('hot-locations-content');

    if (locations.length > 0) {
        let gridHTML = '';

        // 如果有统计信息，显示AI分析覆盖率
        if (statistics) {
            gridHTML += `
                <div class="statistics-info">
                    <div class="stats-item">
                        <span class="stats-label">📊 总校园卡数：</span>
                        <span class="stats-value">${statistics.total_cards}</span>
                    </div>
                    <div class="stats-item">
                        <span class="stats-label">🤖 AI分析覆盖：</span>
                        <span class="stats-value">${statistics.cards_with_ai_analysis}/${statistics.total_cards} (${statistics.ai_analysis_coverage}%)</span>
                    </div>
                    <div class="stats-note">
                        <small>💡 统计基于AI分析后的标准地点名称，确保数据准确性</small>
                    </div>
                </div>
            `;
        }

        gridHTML += '<div class="hot-locations-grid"></div>';
        contentDiv.innerHTML = gridHTML;

        const gridDiv = contentDiv.querySelector('.hot-locations-grid');

        locations.forEach((location, index) => {
            // 根据排名添加不同的样式类
            let rankClass = '';
            if (index === 0) rankClass = 'rank-1';
            else if (index === 1) rankClass = 'rank-2';
            else if (index === 2) rankClass = 'rank-3';

            // 检查是否是原始数据（未经AI分析）
            const isOriginal = location.location.startsWith('[原始]');
            const displayLocation = isOriginal ? location.location.replace('[原始] ', '') : location.location;
            const originalClass = isOriginal ? 'original-data' : '';

            gridDiv.innerHTML += `
                <div class="hot-location-item ${rankClass} ${originalClass}" onclick="searchLocation('${displayLocation}')">
                    <div class="location-name">
                        ${isOriginal ? '📝 ' : '🤖 '}${displayLocation}
                        ${isOriginal ? '<span class="original-tag">原始</span>' : '<span class="ai-tag">AI标准</span>'}
                    </div>
                    <div class="location-count">${location.count}次</div>
                    <div class="location-stats">
                        <div class="location-percentage">占比 ${location.percentage}%</div>
                    </div>
                </div>
            `;
        });
    } else {
        contentDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📍</div>
                <div class="empty-text">暂无热门地点数据</div>
                <div class="empty-hint">当有更多校园卡发现记录时，这里会显示热门地点</div>
            </div>
        `;
    }
}

// 切换图表类型
function switchChart(chartType) {
    currentChartType = chartType;

    // 更新按钮状态
    document.querySelectorAll('.chart-toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-chart="${chartType}"]`).classList.add('active');

    // 切换视图
    document.querySelectorAll('.chart-view').forEach(view => {
        view.classList.remove('active');
    });

    if (chartType === 'grid') {
        document.getElementById('hot-locations-grid').classList.add('active');
    } else {
        document.getElementById('hot-locations-charts').classList.add('active');
        updateChart(chartType);
    }
}

// 更新图表
function updateChart(chartType) {
    if (locationsData.length === 0) {
        document.getElementById('chart-legend').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div class="empty-text">暂无数据</div>
            </div>
        `;
        return;
    }

    const ctx = document.getElementById('locationsChart').getContext('2d');

    // 销毁现有图表
    if (locationsChart) {
        locationsChart.destroy();
    }

    // 准备数据
    const labels = locationsData.map(item => item.location);
    const data = locationsData.map(item => item.count);
    const percentages = locationsData.map(item => item.percentage);

    // 生成颜色
    const colors = generateColors(locationsData.length);

    // 创建新图表
    if (chartType === 'bar') {
        createBarChart(ctx, labels, data, colors);
    } else if (chartType === 'pie') {
        createPieChart(ctx, labels, data, colors);
    }

    // 更新图例
    updateChartLegend(labels, data, percentages, colors);
}

// 创建柱状图
function createBarChart(ctx, labels, data, colors) {
    locationsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '发现次数',
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.8', '1')),
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const percentage = locationsData[context.dataIndex].percentage;
                            return `${context.parsed.y}次 (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const location = locationsData[index].location;
                    searchLocation(location);
                }
            }
        }
    });
}

// 创建饼图
function createPieChart(ctx, labels, data, colors) {
    locationsChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 3,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const percentage = locationsData[context.dataIndex].percentage;
                            return `${context.label}: ${context.parsed}次 (${percentage}%)`;
                        }
                    }
                }
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const location = locationsData[index].location;
                    searchLocation(location);
                }
            }
        }
    });
}

// 生成颜色数组
function generateColors(count) {
    const baseColors = [
        'rgba(255, 224, 178, 0.8)',  // 浅金色
        'rgba(225, 190, 231, 0.8)',  // 浅紫色
        'rgba(200, 230, 201, 0.8)',  // 浅绿色
        'rgba(187, 222, 251, 0.8)',  // 浅蓝色
        'rgba(255, 204, 188, 0.8)',  // 浅橙色
        'rgba(174, 213, 129, 0.8)',  // 浅青绿色
        'rgba(206, 147, 216, 0.8)',  // 浅紫罗兰色
        'rgba(239, 154, 154, 0.8)',  // 浅红色
        'rgba(255, 241, 118, 0.8)',  // 浅黄色
        'rgba(176, 190, 197, 0.8)'   // 浅灰蓝色
    ];

    return baseColors.slice(0, count);
}

// 更新图例
function updateChartLegend(labels, data, percentages, colors) {
    const legendDiv = document.getElementById('chart-legend');

    let legendHTML = '<h4>📊 数据详情</h4>';

    labels.forEach((label, index) => {
        legendHTML += `
            <div class="legend-item" onclick="searchLocation('${label}')" style="cursor: pointer;">
                <div style="display: flex; align-items: center; flex: 1;">
                    <div class="legend-color" style="background-color: ${colors[index]};"></div>
                    <span class="legend-label">${label}</span>
                </div>
                <div>
                    <span class="legend-value">${data[index]}次</span>
                    <span class="legend-percentage">${percentages[index]}%</span>
                </div>
            </div>
        `;
    });

    legendDiv.innerHTML = legendHTML;
}

// 搜索特定地点（点击热门地点时触发）
function searchLocation(location) {
    // 显示该地点的详细信息
    showLocationDetails(location);
}

// 显示地点详细信息
async function showLocationDetails(location) {
    try {
        // 获取该地点的所有校园卡信息
        const result = await apiCall('/query_lost_card?student_id=dummy');

        if (result.unmatched_cards && result.unmatched_cards.length > 0) {
            // 筛选出该地点的校园卡
            const locationCards = result.unmatched_cards.filter(card =>
                card.found_location && card.found_location.includes(location)
            );

            if (locationCards.length > 0) {
                let message = `📍 地点：${location}\n\n`;
                message += `共有 ${locationCards.length} 张校园卡在此地点被发现：\n\n`;

                locationCards.forEach((card, index) => {
                    message += `${index + 1}. 发现时间：${card.found_time}\n`;

                    // 根据是否有真实姓名显示不同的信息
                    if (card.owner_name && card.name_source === 'real') {
                        message += `   卡主姓名：${card.owner_name} (${card.masked_info.student_id})\n\n`;
                    } else {
                        message += `   持卡人：持卡人 (${card.masked_info.student_id})\n\n`;
                    }
                });

                alert(message);
            } else {
                alert(`📍 地点：${location}\n\n该地点暂无未认领的校园卡`);
            }
        } else {
            alert(`📍 地点：${location}\n\n暂无相关校园卡信息`);
        }
    } catch (error) {
        alert(`📍 地点：${location}\n\n获取信息失败，请稍后重试`);
    }
}

// 加载公示列表
async function loadPublicList() {
    try {
        const result = await apiCall('/query_lost_card?student_id=dummy');
        const contentDiv = document.getElementById('public-list-content');

        if (result.unmatched_cards && result.unmatched_cards.length > 0) {
            contentDiv.innerHTML = '<h3>📋 未认领的校园卡</h3>';
            result.unmatched_cards.forEach(card => {
                // 根据处理方式设置不同的图标和样式
                const handlerIcon = card.handler_option === 1 ? '📞' : '📍';
                const handlerClass = card.handler_option === 1 ? 'contact-handler' : 'location-handler';

                // 根据是否有真实姓名显示不同的信息
                let ownerInfo = '';
                if (card.owner_name && card.name_source === 'real') {
                    ownerInfo = `<strong>卡主姓名：</strong>${card.owner_name} (${card.masked_info.student_id})`;
                } else {
                    ownerInfo = `<strong>卡主信息：</strong>持卡人 (${card.masked_info.student_id})`;
                }

                // 检查是否显示删除按钮（只有当前登录用户的记录才显示）
                let deleteButtonHtml = '';
                if (currentUser && card.student_id === currentUser.student_id) {
                    deleteButtonHtml = `
                        <div class="delete-action">
                            <button class="delete-btn" onclick="deleteCardRecord(${card.card_id}, '${card.student_id}')">
                                🗑️ 删除此记录
                            </button>
                            <small class="delete-hint">删除后此记录将不再显示在公示列表中</small>
                        </div>
                    `;
                }

                contentDiv.innerHTML += `
                    <div class="result-item">
                        <p><strong>发现时间：</strong>${card.found_time}</p>
                        <p><strong>发现地点：</strong>${card.found_location}</p>
                        <p>${ownerInfo}</p>
                        <div class="handler-info ${handlerClass}">
                            <p><strong>${handlerIcon} 卡片处理方式：</strong>${card.handler_text}</p>
                            <p><strong>具体信息：</strong>${card.contact_info}</p>
                        </div>
                        ${deleteButtonHtml}
                    </div>
                `;
            });
        } else {
            contentDiv.innerHTML = `
                <h3>📋 未认领的校园卡</h3>
                <div class="empty-state">
                    <div class="empty-icon">🎉</div>
                    <div class="empty-text">暂无未认领的校园卡</div>
                    <div class="empty-hint">所有校园卡都已被认领！</div>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('public-list-content').innerHTML = `
            <h3>📋 未认领的校园卡</h3>
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <div class="empty-text">加载失败</div>
                <div class="empty-hint">请稍后重试</div>
            </div>
        `;
    }
}

// 加载论坛帖子
async function loadForumPosts() {
    try {
        const posts = await apiCall('/forum/posts');
        const postsDiv = document.getElementById('forum-posts');

        if (posts.length > 0) {
            postsDiv.innerHTML = '';
            posts.forEach(post => {
                let postClass = '';
                let postLabel = '';

                if (post.is_ad) {
                    postClass = 'ad';
                    postLabel = '[广告]';
                } else if (post.is_advice) {
                    postClass = 'advice';
                    postLabel = '[建议/反馈]';
                }

                postsDiv.innerHTML += `
                    <div class="post-item ${postClass}">
                        <div class="post-title">${post.title} ${postLabel}</div>
                        <div class="post-meta">作者：${post.author_name} | 发布时间：${post.created_at}</div>
                        <div class="post-content">${post.content}</div>
                    </div>
                `;
            });
        } else {
            postsDiv.innerHTML = '<p>暂无帖子</p>';
        }
    } catch (error) {
        document.getElementById('forum-posts').innerHTML = '<p>加载失败</p>';
    }
}

// 复选框互斥逻辑处理函数
function handleAdChange() {
    const isAdviceCheckbox = document.getElementById('is-advice');
    if (this.checked && isAdviceCheckbox) {
        isAdviceCheckbox.checked = false;
    }
}

function handleAdviceChange() {
    const isAdCheckbox = document.getElementById('is-ad');
    if (this.checked && isAdCheckbox) {
        isAdCheckbox.checked = false;
    }
}

// 发布帖子
document.getElementById('create-post-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!currentUser) {
        alert('请先登录');
        return;
    }

    const title = document.getElementById('post-title').value;
    const content = document.getElementById('post-content').value;
    const isAd = document.getElementById('is-ad').checked;
    const isAdvice = document.getElementById('is-advice').checked;

    try {
        await apiCall('/forum/post', 'POST', {
            title: title,
            content: content,
            author_id: currentUser.user_id,
            is_ad: isAd,
            is_advice: isAdvice
        });

        alert('帖子发布成功！');
        document.getElementById('create-post-form').reset();
        showForum();
    } catch (error) {
        // 错误已在apiCall中处理
    }
});

// 加载奖励列表
async function loadRewards() {
    try {
        const rewards = await apiCall('/rewards');
        const rewardsDiv = document.getElementById('rewards-list');
        
        if (rewards.length > 0) {
            rewardsDiv.innerHTML = '';
            rewards.forEach(reward => {
                const canRedeem = currentUser && currentUser.points >= reward.points_required;
                rewardsDiv.innerHTML += `
                    <div class="reward-item">
                        <div class="reward-info">
                            <h4>${reward.name}</h4>
                            <p>${reward.description}</p>
                        </div>
                        <div>
                            <span class="reward-points">${reward.points_required} 积分</span>
                            <button class="redeem-btn" ${!canRedeem ? 'disabled' : ''} 
                                    onclick="redeemReward(${reward.id}, ${reward.points_required})">
                                ${canRedeem ? '兑换' : '积分不足'}
                            </button>
                        </div>
                    </div>
                `;
            });
        } else {
            rewardsDiv.innerHTML = '<p>暂无奖励</p>';
        }
    } catch (error) {
        document.getElementById('rewards-list').innerHTML = '<p>加载失败</p>';
    }
}

// 兑换奖励
async function redeemReward(rewardId, pointsRequired) {
    if (!currentUser) {
        alert('请先登录');
        return;
    }
    
    if (currentUser.points < pointsRequired) {
        alert('积分不足');
        return;
    }
    
    try {
        const result = await apiCall('/reward/redeem', 'POST', {
            user_id: currentUser.user_id,
            reward_id: rewardId
        });
        
        // 显示兑换成功提示
        alert('恭喜您兑换成功，请您在两周内凭姓名和学号到兑换处领取奖品！');
        currentUser.points = result.remaining_points;
        // 更新localStorage中的用户信息
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        updateUserInfo();
        loadRewards(); // 重新加载奖励列表
    } catch (error) {
        // 错误已在apiCall中处理
    }
}

// 键盘快捷键支持
document.addEventListener('keydown', function(e) {
    // 在查询页面按Escape清空查询
    if (e.key === 'Escape' && document.getElementById('query-card-page').classList.contains('active')) {
        clearQuery();
    }

    // Ctrl+Enter 快速查询
    if (e.ctrlKey && e.key === 'Enter' && document.getElementById('query-card-page').classList.contains('active')) {
        e.preventDefault();
        document.getElementById('query-card-form').dispatchEvent(new Event('submit'));
    }
});

// 删除校园卡记录功能
async function deleteCardRecord(cardId, studentId) {
    // 检查用户是否登录
    if (!currentUser) {
        alert('请先登录');
        return;
    }

    // 检查权限
    if (currentUser.student_id !== studentId) {
        alert('您只能删除自己的记录');
        return;
    }

    // 确认删除
    if (!confirm('确定要删除此记录吗？\n\n删除后：\n• 此记录将不再显示在公示列表中\n• 其他用户将无法看到此校园卡信息\n• 此操作不可撤销')) {
        return;
    }

    try {
        // 显示加载状态
        const deleteButtons = document.querySelectorAll(`button[onclick*="${cardId}"]`);
        deleteButtons.forEach(btn => {
            btn.disabled = true;
            btn.innerHTML = '🔄 删除中...';
        });

        const result = await apiCall('/delete_card_record', 'POST', {
            card_id: cardId,
            current_user_student_id: currentUser.student_id
        });

        if (result.success) {
            alert('✅ 删除成功！\n\n记录已从系统中移除，不再显示在公示列表中。');

            // 刷新当前页面的数据
            if (document.getElementById('query-card-page').classList.contains('active')) {
                // 如果在查询页面，重新执行查询
                const studentIdInput = document.getElementById('query-student-id');
                if (studentIdInput.value.trim()) {
                    document.getElementById('query-card-form').dispatchEvent(new Event('submit'));
                }
            } else if (document.getElementById('public-list-page').classList.contains('active')) {
                // 如果在公示列表页面，重新加载列表
                loadPublicList();
            }
        } else {
            throw new Error(result.error || '删除失败');
        }
    } catch (error) {
        console.error('删除记录失败:', error);
        alert('❌ 删除失败\n\n' + (error.message || '请稍后重试'));

        // 恢复按钮状态
        const deleteButtons = document.querySelectorAll(`button[onclick*="${cardId}"]`);
        deleteButtons.forEach(btn => {
            btn.disabled = false;
            btn.innerHTML = '🗑️ 删除此记录';
        });
    }
}

// 智能地点查询功能
function clearSmartQuery() {
    document.getElementById('location-input').value = '';
    document.getElementById('smart-query-result').innerHTML = '';
    document.getElementById('smart-query-status').style.display = 'none';
    document.getElementById('location-input').focus();

    // 同时清空地图
    clearSmartQueryResults();
}

// 清空智能查询结果和地图
function clearSmartQueryResults() {
    // 清空查询结果区域
    document.getElementById('smart-query-result').innerHTML = '';

    // 隐藏地图区域
    const mapSection = document.getElementById('campus-map-section');
    if (mapSection) {
        mapSection.style.display = 'none';
    }

    // 清空地图标记
    const markersContainer = document.getElementById('map-markers');
    if (markersContainer) {
        markersContainer.innerHTML = '';
    }

    // 清理地图相关的全局状态
    cleanupMapResources();

    // 隐藏任何现有的地图提示框
    hideMapTooltip();
}

// 清理地图资源
function cleanupMapResources() {
    // 清除地图数据
    currentMapData = null;

    // 清除 ResizeObserver
    if (mapResizeObserver) {
        mapResizeObserver.disconnect();
        mapResizeObserver = null;
    }

    // 清除窗口大小变化监听器
    if (window.mapResizeHandler) {
        window.removeEventListener('resize', window.mapResizeHandler);
        window.mapResizeHandler = null;
    }

    // 清除定时器
    if (window.mapResizeTimeout) {
        clearTimeout(window.mapResizeTimeout);
        window.mapResizeTimeout = null;
    }

    console.log('地图资源已清理');
}

// 显示智能查询状态
function showSmartQueryStatus(type, message) {
    const statusDiv = document.getElementById('smart-query-status');
    statusDiv.className = `query-status ${type}`;
    statusDiv.textContent = message;

    // 确保状态元素可见
    statusDiv.style.display = 'block';

    if (type !== 'loading') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

// 智能地点查询表单提交
document.getElementById('smart-location-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const userInput = document.getElementById('location-input').value.trim();

    if (!userInput) {
        showSmartQueryStatus('error', '请输入您的查询内容');
        return;
    }

    // 清空之前的查询结果和地图
    clearSmartQueryResults();

    // 显示加载状态
    showSmartQueryStatus('loading', '🚀 正在快速分析您的查询...');

    try {
        const result = await apiCall('/smart_location_query', 'POST', {
            user_input: userInput
        });

        const resultDiv = document.getElementById('smart-query-result');

        if (result.success) {
            let resultHtml = `
                <div class="smart-result-header">
                    <h3>🎯 查询结果</h3>
                    <p class="parsing-info">
                        <strong>AI识别结果：</strong>${result.parsing_result.reasoning}
                        <span class="confidence-badge">置信度: ${(result.parsing_result.confidence * 100).toFixed(0)}%</span>
                    </p>
                </div>
            `;

            result.results.forEach((locationResult, index) => {
                resultHtml += `
                    <div class="smart-result-item">
                        <div class="location-header">
                            <h4>📍 ${locationResult.location}</h4>
                        </div>
                `;

                if (locationResult.nearest_lost_and_found) {
                    const lostFound = locationResult.nearest_lost_and_found;
                    resultHtml += `
                        <div class="nearest-point-info">
                            <div class="point-details">
                                <div class="point-name">🏢 最近招领点：${lostFound.name}</div>
                                <div class="point-distance">📏 距离：约 ${lostFound.distance} 个单位</div>
                                <div class="point-coordinates">📌 坐标：(${lostFound.coordinates.x}, ${lostFound.coordinates.y})</div>
                            </div>
                        </div>
                        <div class="ai-advice">
                            <div class="advice-header">🤖 AI建议：</div>
                            <div class="advice-content" id="ai-advice-${index}">
                                ${locationResult.ai_advice_loading ?
                                    '<div class="ai-loading">🤖 正在生成智能建议...</div>' :
                                    locationResult.ai_advice}
                            </div>
                        </div>
                    `;
                } else {
                    resultHtml += `
                        <div class="no-point-info">
                            <div class="advice-content">${locationResult.ai_advice}</div>
                        </div>
                    `;
                }

                resultHtml += `</div>`;
            });

            resultDiv.innerHTML = resultHtml;
            const statusMessage = result.results.length > 1
                ? `✅ 成功识别到 ${result.results.length} 个地点！已按语义相关性排序，最相关的地点显示在前面。`
                : `✅ 成功识别到 ${result.results.length} 个地点！`;
            showSmartQueryStatus('success', statusMessage);

            // 显示校园地图
            if (result.map_data && result.map_data.markers.length > 0) {
                displayCampusMap(result.map_data);
            }

            // 异步加载AI建议
            loadAIAdviceForResults(result.results);
        } else {
            resultDiv.innerHTML = `
                <div class="smart-result-item">
                    <div class="no-result">
                        <div class="no-result-icon">🤔</div>
                        <div class="no-result-message">${result.message}</div>
                        <div class="no-result-hint">
                            <p>💡 建议：</p>
                            <ul>
                                <li>尝试使用更具体的地点名称</li>
                                <li>可以描述您的具体需求，如"我在XX地点丢了东西"</li>
                                <li>参考校园地图上的建筑物名称</li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;
            showSmartQueryStatus('error', '❌ 未能识别到有效地点');
        }

        // 滚动到结果区域
        document.getElementById('smart-query-result-section').scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });

    } catch (error) {
        showSmartQueryStatus('error', '❌ 查询失败，请稍后重试');
        document.getElementById('smart-query-result').innerHTML = `
            <div class="smart-result-item">
                <div class="error-result">
                    <div class="error-icon">⚠️</div>
                    <div class="error-message">查询过程中发生错误</div>
                    <div class="error-hint">请检查网络连接或稍后重试</div>
                </div>
            </div>
        `;
    }
});

// 异步加载AI建议
async function loadAIAdviceForResults(results) {
    for (let i = 0; i < results.length; i++) {
        const locationResult = results[i];

        // 只为有招领点的地点加载AI建议
        if (locationResult.nearest_lost_and_found && locationResult.ai_advice_loading) {
            try {
                const adviceElement = document.getElementById(`ai-advice-${i}`);
                if (adviceElement) {
                    // 显示加载动画
                    adviceElement.innerHTML = '<div class="ai-loading">🤖 正在生成智能建议<span class="loading-dots">...</span></div>';

                    // 调用AI建议接口
                    const adviceResult = await apiCall('/get_ai_advice', 'POST', {
                        location_name: locationResult.location,
                        nearest_point: locationResult.nearest_lost_and_found
                    });

                    if (adviceResult.success) {
                        // 流式显示AI建议
                        await typewriterEffect(adviceElement, adviceResult.ai_advice);
                    } else {
                        adviceElement.innerHTML = `<div class="ai-error">❌ AI建议生成失败，请稍后重试</div>`;
                    }
                }
            } catch (error) {
                console.error('AI建议加载失败:', error);
                const adviceElement = document.getElementById(`ai-advice-${i}`);
                if (adviceElement) {
                    adviceElement.innerHTML = `<div class="ai-error">❌ AI建议加载失败</div>`;
                }
            }
        }
    }
}

// 打字机效果显示AI建议
async function typewriterEffect(element, text) {
    element.innerHTML = '';
    const speed = 30; // 打字速度（毫秒）

    for (let i = 0; i < text.length; i++) {
        element.innerHTML += text.charAt(i);
        await new Promise(resolve => setTimeout(resolve, speed));
    }
}

// 全局变量存储当前地图数据
let currentMapData = null;
let mapResizeObserver = null;

// 显示校园地图
function displayCampusMap(mapData) {
    const mapSection = document.getElementById('campus-map-section');
    const markersContainer = document.getElementById('map-markers');

    // 保存地图数据供后续使用
    currentMapData = mapData;

    // 显示地图区域
    mapSection.style.display = 'block';

    // 清空现有标记
    markersContainer.innerHTML = '';

    // 获取地图图片元素
    const mapImage = document.getElementById('campus-map-image');

    // 确保图片完全加载并渲染后再添加标记
    ensureImageLoadedAndAddMarkers(mapImage, mapData.markers, markersContainer);

    // 设置窗口大小变化监听
    setupMapResizeHandler(mapImage, markersContainer);

    // 滚动到地图区域
    setTimeout(() => {
        mapSection.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }, 300);
}

// 确保图片完全加载并添加标记
function ensureImageLoadedAndAddMarkers(mapImage, markers, container) {
    // 移除图片的加载状态类
    mapImage.classList.remove('loaded');

    function onImageReady() {
        console.log('图片加载完成，开始添加标记');
        // 添加加载完成的CSS类
        mapImage.classList.add('loaded');

        // 等待CSS过渡完成后再添加标记
        setTimeout(() => {
            addMapMarkers(markers, container, mapImage);
        }, 300);
    }

    function tryAddMarkers() {
        // 检查图片是否真正加载完成且有有效尺寸
        if (mapImage.complete && mapImage.naturalWidth > 0 && mapImage.offsetWidth > 0) {
            console.log('图片已缓存，直接添加标记');
            onImageReady();
        } else {
            console.log('等待图片加载...');

            // 设置加载超时
            const loadTimeout = setTimeout(() => {
                console.warn('图片加载超时');
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #ff6b6b;">⚠️ 地图加载超时，请刷新页面重试</div>';
            }, 10000);

            // 图片未完全加载，设置加载事件监听
            mapImage.onload = function() {
                clearTimeout(loadTimeout);
                console.log('图片加载事件触发');

                // 等待图片完全渲染
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        onImageReady();
                    });
                });
            };

            // 如果图片加载失败，设置错误处理
            mapImage.onerror = function() {
                clearTimeout(loadTimeout);
                console.error('地图图片加载失败');
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #dc3545;">❌ 地图加载失败，请检查网络连接后刷新页面重试</div>';
            };

            // 强制重新加载图片（防止缓存问题）
            if (!mapImage.src || mapImage.src.indexOf('?') === -1) {
                const timestamp = new Date().getTime();
                const separator = mapImage.src.indexOf('?') === -1 ? '?' : '&';
                mapImage.src = mapImage.src + separator + 't=' + timestamp;
            }
        }
    }

    // 立即尝试添加标记
    tryAddMarkers();
}

// 设置地图大小变化监听
function setupMapResizeHandler(mapImage, markersContainer) {
    // 清除之前的监听器
    if (mapResizeObserver) {
        mapResizeObserver.disconnect();
    }

    // 使用 ResizeObserver 监听图片容器大小变化
    if (window.ResizeObserver) {
        mapResizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                // 防抖处理，避免频繁重新计算
                clearTimeout(window.mapResizeTimeout);
                window.mapResizeTimeout = setTimeout(() => {
                    if (currentMapData && currentMapData.markers) {
                        console.log('检测到地图尺寸变化，重新计算标记位置');
                        markersContainer.innerHTML = '';
                        addMapMarkers(currentMapData.markers, markersContainer, mapImage);
                    }
                }, 100);
            }
        });

        mapResizeObserver.observe(mapImage);
    } else {
        // 降级方案：使用 window resize 事件
        const handleResize = () => {
            clearTimeout(window.mapResizeTimeout);
            window.mapResizeTimeout = setTimeout(() => {
                if (currentMapData && currentMapData.markers) {
                    console.log('检测到窗口大小变化，重新计算标记位置');
                    markersContainer.innerHTML = '';
                    addMapMarkers(currentMapData.markers, markersContainer, mapImage);
                }
            }, 200);
        };

        window.addEventListener('resize', handleResize);

        // 保存引用以便后续清理
        window.mapResizeHandler = handleResize;
    }
}

// 添加地图标记
function addMapMarkers(markers, container, mapImage) {
    // 验证输入参数
    if (!markers || !container || !mapImage) {
        console.error('addMapMarkers: 缺少必要参数');
        return;
    }

    // 验证图片尺寸信息
    if (!mapImage.naturalWidth || !mapImage.naturalHeight || !mapImage.offsetWidth || !mapImage.offsetHeight) {
        console.error('addMapMarkers: 图片尺寸信息无效', {
            naturalWidth: mapImage.naturalWidth,
            naturalHeight: mapImage.naturalHeight,
            offsetWidth: mapImage.offsetWidth,
            offsetHeight: mapImage.offsetHeight
        });
        return;
    }

    // 获取图片容器的边界信息
    const imageRect = mapImage.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();

    // 计算图片的实际显示尺寸和缩放比例
    const scaleX = mapImage.offsetWidth / mapImage.naturalWidth;
    const scaleY = mapImage.offsetHeight / mapImage.naturalHeight;

    console.log('地图标记计算信息:', {
        naturalSize: { width: mapImage.naturalWidth, height: mapImage.naturalHeight },
        displaySize: { width: mapImage.offsetWidth, height: mapImage.offsetHeight },
        scale: { x: scaleX, y: scaleY },
        markersCount: markers.length
    });

    markers.forEach((marker, index) => {
        try {
            // 验证标记坐标
            if (typeof marker.x !== 'number' || typeof marker.y !== 'number') {
                console.warn(`标记 ${index} 坐标无效:`, marker);
                return;
            }

            // 计算标记在缩放后图片中的精确位置
            const x = Math.round(marker.x * scaleX);
            const y = Math.round(marker.y * scaleY);

            // 边界检查
            if (x < 0 || x > mapImage.offsetWidth || y < 0 || y > mapImage.offsetHeight) {
                console.warn(`标记 ${marker.name} 位置超出图片边界:`, { x, y, imageSize: { width: mapImage.offsetWidth, height: mapImage.offsetHeight } });
            }

            // 创建标记元素
            const markerElement = document.createElement('div');
            markerElement.className = `map-marker ${marker.shape || 'circle'}`;

            // 设置位置（使用 transform 而不是 left/top 以获得更好的性能）
            markerElement.style.position = 'absolute';
            markerElement.style.left = x + 'px';
            markerElement.style.top = y + 'px';
            markerElement.style.transform = 'translate(-50%, -50%)';
            markerElement.style.backgroundColor = marker.color || '#007bff';

            // 添加数据属性用于调试
            markerElement.setAttribute('data-original-x', marker.x);
            markerElement.setAttribute('data-original-y', marker.y);
            markerElement.setAttribute('data-scaled-x', x);
            markerElement.setAttribute('data-scaled-y', y);
            markerElement.setAttribute('data-marker-name', marker.name);

            // 添加点击事件和悬停提示
            markerElement.title = marker.name + (marker.distance ? ` (距离: ${marker.distance}米)` : '');

            // 添加悬停效果
            markerElement.addEventListener('mouseenter', function(e) {
                showMapTooltip(e, marker);
            });

            markerElement.addEventListener('mouseleave', function() {
                hideMapTooltip();
            });

            // 添加点击事件
            markerElement.addEventListener('click', function() {
                const debugInfo = `📍 ${marker.name}\n原始坐标: (${marker.x}, ${marker.y})\n显示坐标: (${x}, ${y})\n缩放比例: (${scaleX.toFixed(3)}, ${scaleY.toFixed(3)})${marker.distance ? `\n距离: ${marker.distance}米` : ''}`;
                alert(debugInfo);
            });

            container.appendChild(markerElement);

            console.log(`标记 ${marker.name} 添加成功:`, {
                original: { x: marker.x, y: marker.y },
                scaled: { x, y },
                scale: { x: scaleX, y: scaleY }
            });

        } catch (error) {
            console.error(`添加标记 ${marker.name || index} 时出错:`, error);
        }
    });

    console.log(`成功添加 ${container.children.length} 个地图标记`);
}

// 显示地图提示框
function showMapTooltip(event, marker) {
    // 移除现有提示框
    hideMapTooltip();

    const tooltip = document.createElement('div');
    tooltip.className = 'map-tooltip';
    tooltip.id = 'map-tooltip';

    let tooltipText = marker.name;
    if (marker.distance) {
        tooltipText += `\n距离: ${marker.distance}米`;
    }
    tooltipText += `\n坐标: (${marker.x}, ${marker.y})`;

    tooltip.textContent = tooltipText;
    tooltip.style.whiteSpace = 'pre-line';

    // 定位提示框
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = (rect.left + rect.width / 2) + 'px';
    tooltip.style.top = rect.top + 'px';

    document.body.appendChild(tooltip);
}

// 隐藏地图提示框
function hideMapTooltip() {
    const tooltip = document.getElementById('map-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// 调试工具：检查地图标记位置
function debugMapMarkers() {
    const markers = document.querySelectorAll('.map-marker');
    const mapImage = document.getElementById('campus-map-image');

    if (!mapImage || markers.length === 0) {
        console.log('没有找到地图或标记');
        return;
    }

    console.log('=== 地图标记调试信息 ===');
    console.log('图片信息:', {
        naturalSize: { width: mapImage.naturalWidth, height: mapImage.naturalHeight },
        displaySize: { width: mapImage.offsetWidth, height: mapImage.offsetHeight },
        scale: {
            x: mapImage.offsetWidth / mapImage.naturalWidth,
            y: mapImage.offsetHeight / mapImage.naturalHeight
        }
    });

    markers.forEach((marker, index) => {
        const rect = marker.getBoundingClientRect();
        const mapRect = mapImage.getBoundingClientRect();

        console.log(`标记 ${index + 1} (${marker.getAttribute('data-marker-name')}):`, {
            原始坐标: {
                x: marker.getAttribute('data-original-x'),
                y: marker.getAttribute('data-original-y')
            },
            计算坐标: {
                x: marker.getAttribute('data-scaled-x'),
                y: marker.getAttribute('data-scaled-y')
            },
            实际位置: {
                left: marker.style.left,
                top: marker.style.top
            },
            相对图片位置: {
                x: rect.left - mapRect.left,
                y: rect.top - mapRect.top
            }
        });
    });

    console.log('=== 调试信息结束 ===');
}

// 在控制台中暴露调试函数
window.debugMapMarkers = debugMapMarkers;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 尝试从localStorage恢复用户登录状态
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
            console.log('恢复用户登录状态:', currentUser.full_name);
            showHome(); // 如果有保存的用户信息，直接显示主页
        } catch (error) {
            console.error('恢复用户状态失败:', error);
            localStorage.removeItem('currentUser');
            showLogin(); // 如果恢复失败，显示登录页面
        }
    } else {
        showLogin(); // 默认显示登录页面
    }

    // 初始化查询历史
    updateHistoryDisplay();

    // 启动连接保持机制
    startKeepAlive();
});

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    stopKeepAlive();
});
