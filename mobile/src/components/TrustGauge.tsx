/**
 * Trust Score Gauge – animated SVG visualization.
 *
 * Renders a semi-circular gauge with the farmer's trust score,
 * colour-coded by grade (green → red).
 */
import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Defs, G, LinearGradient, Path, Stop, Text as SvgText } from 'react-native-svg';

interface TrustGaugeProps {
  score: number;       // 0–100
  grade: string;       // AAA … D
  confidence: number;  // 0–1
  size?: number;       // component width/height in px
}

const GRADE_COLORS: Record<string, string> = {
  AAA: '#16a34a',
  AA: '#22c55e',
  A: '#84cc16',
  BBB: '#eab308',
  BB: '#f97316',
  B: '#ef4444',
  C: '#dc2626',
  D: '#7f1d1d',
};

function scoreToPath(score: number, size: number): string {
  const cx = size / 2;
  const cy = size * 0.65;
  const r = size * 0.42;
  const startAngle = Math.PI;
  const endAngle = Math.PI + (score / 100) * Math.PI;

  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = score > 50 ? 1 : 0;

  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
}

export const TrustGauge: React.FC<TrustGaugeProps> = ({
  score,
  grade,
  confidence,
  size = 280,
}) => {
  const animatedScore = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(animatedScore, {
      toValue: score,
      duration: 1200,
      useNativeDriver: false,
    }).start();
  }, [score]);

  const color = GRADE_COLORS[grade] || '#6b7280';

  return (
    <View style={[styles.container, { width: size, height: size * 0.72 }]}>
      <Svg width={size} height={size * 0.72}>
        <Defs>
          <LinearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0%" stopColor="#ef4444" />
            <Stop offset="50%" stopColor="#eab308" />
            <Stop offset="100%" stopColor="#16a34a" />
          </LinearGradient>
        </Defs>
        {/* Background arc */}
        <Path
          d={scoreToPath(100, size)}
          stroke="#e5e7eb"
          strokeWidth={18}
          fill="none"
          strokeLinecap="round"
        />
        {/* Score arc */}
        <Path
          d={scoreToPath(score, size)}
          stroke={color}
          strokeWidth={18}
          fill="none"
          strokeLinecap="round"
        />
        {/* Score text */}
        <SvgText
          x={size / 2}
          y={size * 0.56}
          textAnchor="middle"
          fontSize={size * 0.18}
          fontWeight="bold"
          fill={color}
        >
          {Math.round(score)}
        </SvgText>
        {/* Grade label */}
        <SvgText
          x={size / 2}
          y={size * 0.68}
          textAnchor="middle"
          fontSize={size * 0.09}
          fill="#374151"
        >
          Grade {grade}
        </SvgText>
      </Svg>
      <Text style={styles.confidenceText}>
        Confidence: {(confidence * 100).toFixed(0)}%
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  confidenceText: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
});

export default TrustGauge;
