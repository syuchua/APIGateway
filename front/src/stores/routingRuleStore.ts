import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  RoutingRule,
  RoutingRuleSimple,
  CreateRoutingRuleDto,
  UpdateRoutingRuleDto,
} from '@/types/api';
import { apiClient } from '@/lib/api/client';

interface RoutingRuleState {
  rules: RoutingRuleSimple[];
  loading: boolean;
  error: string | null;

  fetchRules: () => Promise<void>;
  fetchDetail: (id: string) => Promise<RoutingRule | null>;
  createRule: (payload: CreateRoutingRuleDto) => Promise<boolean>;
  updateRule: (id: string, payload: UpdateRoutingRuleDto) => Promise<boolean>;
  deleteRule: (id: string) => Promise<boolean>;
  toggleActive: (rule: RoutingRuleSimple) => Promise<boolean>;
  togglePublish: (rule: RoutingRuleSimple) => Promise<boolean>;
  reloadRule: (id: string) => Promise<boolean>;

  clearError: () => void;
}

export const useRoutingRuleStore = create<RoutingRuleState>()(
  devtools(
    (set, get) => ({
      rules: [],
      loading: false,
      error: null,

      async fetchRules() {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.routingRulesV2.listSimple();
          if (response.success && response.data) {
            set({
              rules: response.data.items || [],
              loading: false,
            });
          } else {
            set({
              error: response.error || '获取路由规则列表失败',
              loading: false,
            });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误',
            loading: false,
          });
        }
      },

      async fetchDetail(id) {
        try {
          const response = await apiClient.routingRulesV2.get(id);
          if (response.success && response.data) {
            return response.data;
          }
          set({ error: response.error || '获取路由规则详情失败' });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误',
          });
        }
        return null;
      },

      async createRule(payload) {
        try {
          const response = await apiClient.routingRulesV2.create(payload);
          if (response.success) {
            await get().fetchRules();
            return true;
          }
          set({ error: response.error || '创建路由规则失败' });
          return false;
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '网络错误' });
          return false;
        }
      },

      async updateRule(id, payload) {
        try {
          const response = await apiClient.routingRulesV2.update(id, payload);
          if (response.success) {
            await get().fetchRules();
            return true;
          }
          set({ error: response.error || '更新路由规则失败' });
          return false;
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '网络错误' });
          return false;
        }
      },

      async deleteRule(id) {
        try {
          const response = await apiClient.routingRulesV2.delete(id);
          if (response.success) {
            await get().fetchRules();
            return true;
          }
          set({ error: response.error || '删除路由规则失败' });
          return false;
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '网络错误' });
          return false;
        }
      },

      async toggleActive(rule) {
        return get().updateRule(rule.id, { is_active: !rule.is_active });
      },

      async togglePublish(rule) {
        try {
          const response = rule.is_published
            ? await apiClient.routingRulesV2.unpublish(rule.id)
            : await apiClient.routingRulesV2.publish(rule.id);

          if (response.success) {
            await get().fetchRules();
            return true;
          }

          set({ error: response.error || '更新发布状态失败' });
          return false;
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '网络错误' });
          return false;
        }
      },

      async reloadRule(id) {
        try {
          const response = await apiClient.routingRulesV2.reload(id);
          if (response.success) {
            return true;
          }
          set({ error: response.error || '重新加载路由规则失败' });
          return false;
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '网络错误' });
          return false;
        }
      },

      clearError() {
        set({ error: null });
      },
    }),
    { name: 'routing-rule-store' }
  )
);

export default useRoutingRuleStore;
