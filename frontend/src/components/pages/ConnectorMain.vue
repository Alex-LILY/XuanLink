<script setup>
import { reactive, ref, shallowRef } from 'vue';
import IconRun from '../icons/iconRun.vue';
import IconSetting from '../icons/iconSetting.vue';
import IconPlug from '../icons/iconPlug.vue';
import IconPlus from '../icons/iconPlus.vue';
import LoadingButton from '../LoadingButton.vue';
import { getDataOrPopupError } from '@/assets/utils';
import { useRouter } from 'vue-router';
import { t } from '@/i18n';

const router = useRouter()

const connectors = ref([
    // {
    //     "connector_type": "",
    //     "connector_id": "",
    //     "name": "反弹Shell",
    //     "note": "《原神》是由米哈游自主研发的一款全新开放世界冒险游戏。",
    //     "connection": {},
    //     "autostart": false,
    // },
]);

const connectorStatus = reactive({

})

async function fetchConnectors() {
    let allConnectors = await getDataOrPopupError("/connector/all")
    console.log(allConnectors)
    connectors.value = allConnectors
    let startedConnectors = await getDataOrPopupError("/connector/started")
    for (let connector of allConnectors) {
        connectorStatus[connector.connector_id] = "off"
    }
    console.log(startedConnectors)
    for (let connectorId of startedConnectors) {
        connectorStatus[connectorId] = "on"
    }
}

setTimeout(fetchConnectors, 0)

async function connectorSwitch(connectorId) {
    console.log(connectorId)
    let lastStatus = connectorStatus[connectorId];
    connectorStatus[connectorId] = "loading"
    try {
        if (lastStatus == "off") {
            await getDataOrPopupError(`/connector/${connectorId}/start`)
            connectorStatus[connectorId] = "on"
        } else {
            await getDataOrPopupError(`/connector/${connectorId}/stop`)
            connectorStatus[connectorId] = "off"
        }
    } finally {
        await fetchConnectors()
    }
}

function editConnector(connectorId) {
    router.push(`/connector-editor/${connectorId}`)
}

</script>

<template>
    <div class="page-container">
        <div class="page-toolbar">
            <span class="page-hint">{{ t.connector.hint }}</span>
            <button class="tool-btn primary" @click="router.push('/connector-editor/')">
                <IconPlus />
                {{ t.connector.newListener }}
            </button>
        </div>

        <div class="table-card shadow-box" v-if="connectors.length != 0">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>{{ t.connector.colName }}</th>
                        <th>{{ t.connector.colProtocol }}</th>
                        <th>{{ t.connector.colListen }}</th>
                        <th>{{ t.connector.colReturn }}</th>
                        <th>{{ t.connector.colConns }}</th>
                        <th>{{ t.connector.colStatus }}</th>
                        <th>{{ t.connector.colOps }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="connector in connectors" :key="connector.connector_id">
                        <td class="mono">{{ connector.connector_id.slice(0, 8) }}</td>
                        <td class="connector-name-cell">{{ connector.name }}</td>
                        <td>{{ connector.connector_type }}</td>
                        <td class="mono">{{ connector.connection?.listen_host }}:{{ connector.connection?.listen_port }}</td>
                        <td class="mono">-</td>
                        <td>0</td>
                        <td>
                            <span class="status-badge" :data-status="connectorStatus[connector.connector_id]">
                                {{ connectorStatus[connector.connector_id] === 'on' ? t.connector.running : t.connector.stopped }}
                            </span>
                        </td>
                        <td>
                            <div class="row-actions">
                                <div class="loading-btn-wrap" :title="t.connector.toggleTitle" @click="connectorSwitch(connector.connector_id)">
                                    <LoadingButton :status="connectorStatus[connector.connector_id]" />
                                </div>
                                <button class="icon-btn" :title="t.connector.settingsTitle" @click="editConnector(connector.connector_id)">
                                    <IconSetting />
                                </button>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="empty-state" v-else>
            <IconPlug></IconPlug>
            <p>{{ t.connector.emptyHint }}</p>
        </div>
    </div>
</template>

<style scoped>
.page-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
}

.page-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding: 0 4px;
}

.page-hint {
    font-size: var(--font-size-base);
    color: var(--font-color-secondary);
}

.tool-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: var(--control-height);
    padding: 0 16px;
    border-radius: var(--button-radius);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    border: none;
    cursor: pointer;
    transition: background var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
}

.tool-btn svg {
    width: 16px;
    height: 16px;
    stroke: currentColor;
}

.tool-btn.primary {
    background: var(--button-bg);
    color: var(--button-color);
    box-shadow: var(--shadow-button);
}

.tool-btn.primary:hover {
    background: var(--button-hover-bg);
    transform: translateY(-1px);
}

.tool-btn.primary:active {
    transform: translateY(0);
}

.table-card {
    background-color: var(--card-bg);
    border: var(--card-border);
    border-radius: var(--card-radius);
    box-shadow: var(--card-shadow);
    backdrop-filter: var(--card-backdrop);
    -webkit-backdrop-filter: var(--card-backdrop);
    overflow: hidden;
    overflow-x: auto;
    flex: 1;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-base);
}

.data-table th,
.data-table td {
    padding: 12px 14px;
    text-align: left;
    border-bottom: 1px solid var(--table-border-color, var(--border-color-grey));
    vertical-align: middle;
    white-space: nowrap;
}

.data-table th {
    background-color: var(--table-header-bg);
    color: var(--table-header-color, var(--font-color-secondary));
    font-weight: var(--font-weight-medium);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

.data-table tbody tr {
    cursor: default;
    transition: background-color var(--transition-fast);
}

.data-table tbody tr:hover {
    background-color: var(--table-row-hover-bg);
}

.connector-name-cell {
    font-weight: var(--font-weight-medium);
    color: var(--font-color-primary);
}

.mono {
    font-family: var(--font-mono);
    color: var(--font-color-secondary);
    font-size: 0.85rem;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: var(--radius-pill);
    font-size: 0.8rem;
    font-weight: var(--font-weight-medium);
}

.status-badge[data-status="on"] {
    background-color: rgba(74, 222, 128, 0.15);
    color: var(--green);
    border: 1px solid rgba(74, 222, 128, 0.3);
}

.status-badge[data-status="off"] {
    background-color: var(--background-color-3);
    color: var(--font-color-secondary);
    border: 1px solid var(--border-color-grey);
}

.status-badge[data-status="loading"] {
    background-color: rgba(250, 204, 21, 0.15);
    color: var(--yellow);
    border: 1px solid rgba(250, 204, 21, 0.3);
}

.row-actions {
    display: flex;
    gap: 8px;
}

.icon-btn {
    width: var(--icon-btn-size);
    height: var(--icon-btn-size);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--icon-btn-radius);
    border: 1px solid var(--border-color-grey);
    background-color: var(--icon-btn-bg);
    color: var(--icon-btn-color);
    cursor: pointer;
    transition: background-color var(--transition-fast), color var(--transition-fast);
}

.icon-btn:hover {
    background-color: var(--icon-btn-hover-bg);
    color: var(--font-color-primary);
}

.icon-btn svg {
    width: 16px;
    height: 16px;
    stroke: currentColor;
}

.loading-btn-wrap {
    width: var(--icon-btn-size);
    height: var(--icon-btn-size);
    border-radius: var(--icon-btn-radius);
    overflow: hidden;
    cursor: pointer;
    border: 1px solid var(--border-color-grey);
    background-color: var(--icon-btn-bg);
    display: flex;
    align-items: center;
    justify-content: center;
}

.loading-btn-wrap :deep(.loading-button) {
    width: 100%;
    height: 100%;
    border-radius: var(--icon-btn-radius);
}

.loading-btn-wrap :deep(.loading-button) svg {
    width: 16px;
    height: 16px;
}

.empty-state {
    width: 100%;
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: var(--card-bg);
    border: var(--card-border);
    border-radius: var(--card-radius);
    box-shadow: var(--card-shadow);
    backdrop-filter: var(--card-backdrop);
    -webkit-backdrop-filter: var(--card-backdrop);
}

.empty-state svg {
    width: 80px;
    height: 80px;
    stroke: var(--border-color-grey);
    opacity: 0.6;
}

.empty-state p {
    font-size: 1rem;
    color: var(--font-color-secondary);
    margin-top: 16px;
}
</style>
