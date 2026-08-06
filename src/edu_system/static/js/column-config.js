/**
 * 列配置持久化工具
 * 支持 localStorage（前端优先）和后端 API（多端同步）双模式
 */

const COLUMN_CONFIG_KEY = 'edu:column-config:v1';
const API_BASE = '/api/meta/column-config';

// 默认列配置（各页面各自维护 defaults）
const DEFAULTS = {
    'students/student_list': [
        { field: 'student_no', title: '学号', visible: true, width: 100 },
        { field: 'name', title: '姓名', visible: true, width: 100 },
        { field: 'gender', title: '性别', visible: true, width: 80 },
        { field: 'class_name', title: '班级', visible: true, width: 120 },
        { field: 'grade', title: '年级', visible: true, width: 80 },
        { field: 'status', title: '状态', visible: true, width: 100 },
    ],
    'scores/score_entry': [
        { field: 'student_no', title: '学号', visible: true, width: 100 },
        { field: 'name', title: '姓名', visible: true, width: 100 },
        { field: 'subject', title: '科目', visible: true, width: 100 },
        { field: 'score', title: '成绩', visible: true, width: 80 },
        { field: 'rank', title: '排名', visible: true, width: 80 },
    ],
    'exams/exam_manage': [
        { field: 'name', title: '考试名称', visible: true, width: 180 },
        { field: 'exam_type', title: '类型', visible: true, width: 100 },
        { field: 'semester_label', title: '学期', visible: true, width: 120 },
        { field: 'start_date', title: '开始日期', visible: true, width: 120 },
        { field: 'end_date', title: '结束日期', visible: true, width: 120 },
        { field: 'status', title: '状态', visible: true, width: 100 },
    ],
    'teachers/teacher_list': [
        { field: 'staff_no', title: '工号', visible: true, width: 100 },
        { field: 'name', title: '姓名', visible: true, width: 100 },
        { field: 'gender', title: '性别', visible: true, width: 80 },
        { field: 'title', title: '职称', visible: true, width: 100 },
        { field: 'department', title: '部门', visible: true, width: 120 },
        { field: 'phone', title: '电话', visible: true, width: 120 },
    ],
    'system/system_config': [
        { field: 'name', title: '服务名称', visible: true, width: 180 },
        { field: 'description', title: '描述', visible: true, width: 250 },
        { field: 'enabled', title: '状态', visible: true, width: 100 },
    ],
    'audit/logs': [
        { field: 'created_at', title: '时间', visible: true, width: 160 },
        { field: 'service_code', title: '服务', visible: true, width: 120 },
        { field: 'method', title: '方法', visible: true, width: 80 },
        { field: 'path', title: '路径', visible: true, width: 300 },
    ],
};

// 生成配置键（页面级）
function getConfigKey(pageId) {
    return `${COLUMN_CONFIG_KEY}:${pageId}`;
}

// 获取配置（localStorage 优先，回退默认值）
export function getColumnConfig(pageId) {
    const key = getConfigKey(pageId);
    try {
        const stored = localStorage.getItem(key);
        if (stored) {
            const parsed = JSON.parse(stored);
            // 合并默认值（处理新增列）
            const defaults = DEFAULTS[pageId] || [];
            return mergeWithDefaults(parsed, defaults);
        }
    } catch (e) {
        console.warn('Failed to parse column config:', e);
    }
    return DEFAULTS[pageId] || [];
}

// 保存配置到 localStorage
export function saveColumnConfig(pageId, columns) {
    const key = getConfigKey(pageId);
    try {
        localStorage.setItem(key, JSON.stringify(columns));
        return true;
    } catch (e) {
        console.error('Failed to save column config:', e);
        return false;
    }
}

// 合并默认值（保留用户自定义顺序/可见性，新增默认列）
function mergeWithDefaults(stored, defaults) {
    const storedMap = new Map(stored.map(c => [c.field, c]));
    return defaults.map(def => {
        const user = storedMap.get(def.field);
        if (user) {
            return { ...def, visible: user.visible ?? def.visible, width: user.width ?? def.width };
        }
        return def;
    });
}

// 重置为默认
export function resetColumnConfig(pageId) {
    const key = getConfigKey(pageId);
    localStorage.removeItem(key);
    return DEFAULTS[pageId] || [];
}

// 后端 API：获取用户列配置（多端同步用）
export async function fetchColumnConfigFromServer(pageId) {
    try {
        const resp = await fetch(`${API_BASE}/${encodeURIComponent(pageId)}`, {
            credentials: 'include',
            headers: window.authHeaders ? window.authHeaders() : {},
        });
        if (resp.ok) {
            return (await resp.json()).columns || [];
        }
    } catch (e) {
        console.warn('Failed to fetch column config from server:', e);
    }
    return null;
}

// 后端 API：保存用户列配置
export async function saveColumnConfigToServer(pageId, columns) {
    try {
        const resp = await fetch(`${API_BASE}/${encodeURIComponent(pageId)}`, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...(window.authHeaders ? window.authHeaders() : {}),
            },
            body: JSON.stringify({ columns }),
        });
        return resp.ok;
    } catch (e) {
        console.error('Failed to save column config to server:', e);
        return false;
    }
}

// 同步策略：localStorage -> server（登录后触发）
export async function syncColumnConfigToServer(pageId) {
    const local = getColumnConfig(pageId);
    await saveColumnConfigToServer(pageId, local);
}

// 初始化同步（登录成功后调用）
export async function initColumnConfigSync() {
    const pages = Object.keys(DEFAULTS);
    for (const pageId of pages) {
        await syncColumnConfigToServer(pageId);
    }
}

export { DEFAULTS, COLUMN_CONFIG_KEY };