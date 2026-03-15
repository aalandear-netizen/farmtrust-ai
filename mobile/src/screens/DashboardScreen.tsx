/**
 * Farmer Dashboard – main home screen.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { TrustGauge } from '../components/TrustGauge';
import { trustScoreApi } from '../services/api';
import { useStore } from '../store/useStore';

interface Loan {
  id: string;
  loan_number: string;
  amount: number;
  status: string;
}

export default function DashboardScreen() {
  const { user } = useStore();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [trustScore, setTrustScore] = useState<{
    score: number;
    grade: string;
    confidence: number;
    explanation: string;
  } | null>(null);

  const fetchData = useCallback(async () => {
    if (!user?.id) return;
    try {
      const ts = await trustScoreApi.getLatest(user.id);
      setTrustScore(ts.data);
    } catch {
      // score may not be computed yet
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.greeting}>Welcome, {user?.email?.split('@')[0]} 👋</Text>
        <Text style={styles.subtitle}>Your agricultural financial dashboard</Text>
      </View>

      {/* Trust Score Gauge */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Trust Score</Text>
        {trustScore ? (
          <>
            <TrustGauge
              score={trustScore.score}
              grade={trustScore.grade}
              confidence={trustScore.confidence}
              size={260}
            />
            <Text style={styles.explanation}>{trustScore.explanation}</Text>
          </>
        ) : (
          <Text style={styles.noData}>No trust score computed yet.</Text>
        )}
      </View>

      {/* Quick Actions */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          {[
            { label: '💰 Apply for Loan', color: '#16a34a' },
            { label: '🌾 Insurance', color: '#0284c7' },
            { label: '🏪 Market', color: '#9333ea' },
            { label: '🏛️ Schemes', color: '#ea580c' },
          ].map((action) => (
            <TouchableOpacity
              key={action.label}
              style={[styles.actionBtn, { borderColor: action.color }]}
            >
              <Text style={[styles.actionBtnText, { color: action.color }]}>
                {action.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { backgroundColor: '#16a34a', padding: 24, paddingTop: 60 },
  greeting: { fontSize: 22, fontWeight: 'bold', color: '#fff' },
  subtitle: { fontSize: 14, color: '#dcfce7', marginTop: 4 },
  card: {
    backgroundColor: '#fff',
    margin: 16,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: { fontSize: 18, fontWeight: '600', color: '#111827', marginBottom: 12 },
  explanation: { fontSize: 13, color: '#6b7280', textAlign: 'center', marginTop: 8 },
  noData: { color: '#9ca3af', textAlign: 'center', paddingVertical: 24 },
  actionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 4 },
  actionBtn: {
    borderWidth: 1.5,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    width: '47%',
    alignItems: 'center',
  },
  actionBtnText: { fontSize: 13, fontWeight: '600' },
});
