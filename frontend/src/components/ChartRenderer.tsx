import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';
import { ChartBarIcon, ArrowTrendingUpIcon } from '@heroicons/react/24/outline';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface Chart {
  type: 'line' | 'bar' | 'pie' | 'doughnut';
  title: string;
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
      fill?: boolean;
    }[];
  };
  description?: string;
}

interface ChartRendererProps {
  charts: Chart[];
}

const getChartIcon = (type: string) => {
  switch (type) {
    case 'line':
      return <ArrowTrendingUpIcon className="h-4 w-4" />;
    case 'bar':
      return <ChartBarIcon className="h-4 w-4" />;
    case 'pie':
    case 'doughnut':
      return <div className="w-4 h-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600"></div>;
    default:
      return <ChartBarIcon className="h-4 w-4" />;
  }
};

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
      labels: {
        font: {
          size: 12,
        },
        usePointStyle: true,
        padding: 20,
      },
    },
    title: {
      display: false, // We'll handle title in the component
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: '#fff',
      bodyColor: '#fff',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
      },
      ticks: {
        font: {
          size: 11,
        },
      },
    },
    y: {
      grid: {
        color: 'rgba(0, 0, 0, 0.05)',
      },
      ticks: {
        font: {
          size: 11,
        },
      },
    },
  },
};

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right' as const,
      labels: {
        font: {
          size: 12,
        },
        usePointStyle: true,
        padding: 15,
      },
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: '#fff',
      bodyColor: '#fff',
    },
  },
};

export default function ChartRenderer({ charts }: ChartRendererProps) {
  if (!charts || charts.length === 0) {
    return null;
  }

  const renderChart = (chart: Chart, index: number) => {
    const chartId = `chart-${index}`;
    
    return (
      <div key={chartId} className="bg-white border border-gray-200 rounded-xl p-6 shadow-lg">
        <div className="flex items-center mb-4">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mr-3 text-white">
            {getChartIcon(chart.type)}
          </div>
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-gray-800">{chart.title}</h4>
            {chart.description && (
              <p className="text-sm text-gray-600 mt-1">{chart.description}</p>
            )}
          </div>
        </div>
        
        <div className="relative" style={{ height: '300px' }}>
          {chart.type === 'line' && (
            <Line data={chart.data} options={chartOptions} />
          )}
          {chart.type === 'bar' && (
            <Bar data={chart.data} options={chartOptions} />
          )}
          {(chart.type === 'pie' || chart.type === 'doughnut') && (
            <Pie data={chart.data} options={pieOptions} />
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-lg flex items-center justify-center mr-3">
          <ChartBarIcon className="h-4 w-4 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-gray-800">Data Visualizations</h3>
      </div>
      
      <div className={`grid gap-6 ${charts.length === 1 ? 'grid-cols-1' : charts.length === 2 ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1 xl:grid-cols-2'}`}>
        {charts.map((chart, index) => renderChart(chart, index))}
      </div>
    </div>
  );
}