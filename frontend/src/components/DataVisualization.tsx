import { useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  Filler
} from 'chart.js';
import { Line, Bar, Pie, Doughnut, Radar } from 'react-chartjs-2';
import { ChartBarIcon, ArrowTrendingUpIcon, ChartPieIcon } from '@heroicons/react/24/outline';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  Filler
);

interface ChartData {
  type: 'line' | 'bar' | 'pie' | 'doughnut' | 'radar';
  title: string;
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
      fill?: boolean;
      tension?: number;
    }>;
  };
  options?: any;
}

interface DataVisualizationProps {
  charts: ChartData[];
  insights?: string[];
}

export default function DataVisualization({ charts, insights }: DataVisualizationProps) {
  if (!charts || charts.length === 0) {
    return null;
  }

  const getChartIcon = (type: string) => {
    switch (type) {
      case 'line':
        return ArrowTrendingUpIcon;
      case 'bar':
        return ChartBarIcon;
      case 'pie':
      case 'doughnut':
        return ChartPieIcon;
      default:
        return ChartBarIcon;
    }
  };

  const getDefaultOptions = (type: string, title: string) => {
    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top' as const,
          labels: {
            usePointStyle: true,
            padding: 20,
            font: {
              family: 'system-ui, -apple-system, sans-serif',
              size: 12,
              weight: '500'
            }
          }
        },
        title: {
          display: true,
          text: title,
          font: {
            family: 'system-ui, -apple-system, sans-serif',
            size: 16,
            weight: 'bold'
          },
          padding: {
            top: 10,
            bottom: 30
          }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#ffffff',
          bodyColor: '#ffffff',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          cornerRadius: 8,
          displayColors: false,
          titleFont: {
            size: 14,
            weight: 'bold'
          },
          bodyFont: {
            size: 13
          }
        }
      }
    };

    if (type === 'line' || type === 'bar') {
      return {
        ...baseOptions,
        scales: {
          x: {
            grid: {
              color: 'rgba(0, 0, 0, 0.05)',
              drawBorder: false
            },
            ticks: {
              font: {
                size: 11,
                weight: '500'
              },
              color: '#6B7280'
            }
          },
          y: {
            grid: {
              color: 'rgba(0, 0, 0, 0.05)',
              drawBorder: false
            },
            ticks: {
              font: {
                size: 11,
                weight: '500'
              },
              color: '#6B7280'
            },
            beginAtZero: true
          }
        }
      };
    }

    return baseOptions;
  };

  const getModernColors = (index: number) => {
    const colorSets = [
      {
        background: 'rgba(59, 130, 246, 0.1)',
        border: 'rgb(59, 130, 246)',
        solid: 'rgb(59, 130, 246)'
      },
      {
        background: 'rgba(16, 185, 129, 0.1)',
        border: 'rgb(16, 185, 129)',
        solid: 'rgb(16, 185, 129)'
      },
      {
        background: 'rgba(139, 92, 246, 0.1)',
        border: 'rgb(139, 92, 246)',
        solid: 'rgb(139, 92, 246)'
      },
      {
        background: 'rgba(245, 101, 101, 0.1)',
        border: 'rgb(245, 101, 101)',
        solid: 'rgb(245, 101, 101)'
      },
      {
        background: 'rgba(251, 191, 36, 0.1)',
        border: 'rgb(251, 191, 36)',
        solid: 'rgb(251, 191, 36)'
      }
    ];
    return colorSets[index % colorSets.length];
  };

  const enhanceChartData = (chart: ChartData) => {
    const enhancedData = { ...chart.data };
    
    // Apply modern styling to datasets
    enhancedData.datasets = enhancedData.datasets.map((dataset, index) => {
      const colors = getModernColors(index);
      
      if (chart.type === 'pie' || chart.type === 'doughnut') {
        // Multi-color pie charts
        const pieColors = chart.data.labels.map((_, i) => getModernColors(i).solid);
        return {
          ...dataset,
          backgroundColor: pieColors,
          borderColor: '#ffffff',
          borderWidth: 2,
          hoverBorderWidth: 3
        };
      } else if (chart.type === 'line') {
        return {
          ...dataset,
          backgroundColor: colors.background,
          borderColor: colors.border,
          borderWidth: 3,
          pointBackgroundColor: colors.border,
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8,
          fill: true,
          tension: 0.4
        };
      } else {
        return {
          ...dataset,
          backgroundColor: colors.background,
          borderColor: colors.border,
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false
        };
      }
    });

    return enhancedData;
  };

  const renderChart = (chart: ChartData, index: number) => {
    const enhancedData = enhanceChartData(chart);
    const options = chart.options || getDefaultOptions(chart.type, chart.title);
    const ChartIcon = getChartIcon(chart.type);

    switch (chart.type) {
      case 'line':
        return <Line data={enhancedData} options={options} />;
      case 'bar':
        return <Bar data={enhancedData} options={options} />;
      case 'pie':
        return <Pie data={enhancedData} options={options} />;
      case 'doughnut':
        return <Doughnut data={enhancedData} options={options} />;
      case 'radar':
        return <Radar data={enhancedData} options={options} />;
      default:
        return <Bar data={enhancedData} options={options} />;
    }
  };

  return (
    <div className="mt-6 space-y-8">
      {/* Visual Insights Header */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-6 border border-blue-200/50">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <ChartBarIcon className="h-4 w-4 text-white" />
          </div>
          <h3 className="text-xl font-bold text-gray-900">Visual Insights</h3>
        </div>
        <p className="text-gray-700">Interactive charts and trends based on your data analysis</p>
      </div>

      {/* Charts Grid */}
      <div className={`grid gap-8 ${charts.length === 1 ? 'grid-cols-1' : charts.length === 2 ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1 lg:grid-cols-2'}`}>
        {charts.map((chart, index) => {
          const ChartIcon = getChartIcon(chart.type);
          
          return (
            <div key={index} className="bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 shadow-lg overflow-hidden">
              {/* Chart Header */}
              <div className="p-6 pb-4 border-b border-gray-200/50 bg-gradient-to-r from-gray-50 to-gray-100">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                    <ChartIcon className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <h4 className="font-bold text-gray-900">{chart.title}</h4>
                    <p className="text-sm text-gray-600 capitalize">{chart.type} Chart</p>
                  </div>
                </div>
              </div>
              
              {/* Chart Container */}
              <div className="p-6">
                <div className="h-80 relative">
                  {renderChart(chart, index)}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Chart Insights */}
      {insights && insights.length > 0 && (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 shadow-lg">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center">
              <ArrowTrendingUpIcon className="h-4 w-4 text-white" />
            </div>
            <h4 className="text-lg font-bold text-gray-900">Chart Analysis</h4>
          </div>
          <div className="space-y-3">
            {insights.map((insight, index) => (
              <div key={index} className="flex items-start space-x-3 p-3 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl border border-emerald-200/50">
                <div className="w-6 h-6 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-full flex items-center justify-center shadow-sm mt-0.5">
                  <span className="text-white text-xs font-bold">{index + 1}</span>
                </div>
                <p className="text-gray-800 leading-relaxed font-medium">{insight}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}