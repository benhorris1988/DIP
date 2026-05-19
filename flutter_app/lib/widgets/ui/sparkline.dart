import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

class Sparkline extends StatelessWidget {
  const Sparkline({
    super.key,
    required this.data,
    this.width = 80,
    this.height = 22,
    this.color = const Color(0xFF10B981),
  });

  final List<num> data;
  final double width;
  final double height;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final pts = (data.isEmpty ? const [0, 0] : data)
        .toList()
        .asMap()
        .entries
        .map((e) => FlSpot(e.key.toDouble(), e.value.toDouble()))
        .toList();
    return SizedBox(
      width: width,
      height: height,
      child: LineChart(
        LineChartData(
          gridData: const FlGridData(show: false),
          titlesData: const FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          lineTouchData: const LineTouchData(enabled: false),
          minY: pts.map((p) => p.y).reduce((a, b) => a < b ? a : b),
          maxY: pts.map((p) => p.y).reduce((a, b) => a > b ? a : b) + 0.0001,
          lineBarsData: [
            LineChartBarData(
              spots: pts,
              isCurved: true,
              barWidth: 1.6,
              color: color,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [color.withOpacity(0.35), color.withOpacity(0)],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
