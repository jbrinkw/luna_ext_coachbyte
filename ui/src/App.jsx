import React, { useEffect, useState } from 'react';
import DayDetail from './DayDetail';
import PRTracker from './PRTracker';
import SplitPlanner from './SplitPlanner';
import EditSplitPage from './EditSplitPage';
import { format, parseISO } from 'date-fns';
import { API_BASE } from './api';

const DAY_START_TIME = import.meta.env.DAY_START_TIME || '00:00';
const DAY_TIME_ZONE = import.meta.env.DAY_TIME_ZONE || 'America/New_York';

function parseDayStartMinutes(value) {
  if (!value || typeof value !== 'string') return 0;
  const raw = value.trim();
  if (!raw) return 0;
  let hoursStr;
  let minutesStr;
  if (raw.includes(':')) {
    [hoursStr, minutesStr] = raw.split(':', 2);
  } else if (/^\d{3,4}$/.test(raw)) {
    const padded = raw.padStart(4, '0');
    hoursStr = padded.slice(0, 2);
    minutesStr = padded.slice(2);
  } else {
    return 0;
  }
  const hours = Math.min(Math.max(parseInt(hoursStr, 10) || 0, 0), 23);
  const minutes = Math.min(Math.max(parseInt(minutesStr, 10) || 0, 0), 59);
  return hours * 60 + minutes;
}

const DAY_START_MINUTES = parseDayStartMinutes(DAY_START_TIME);

function getCurrentDayIso() {
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: DAY_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
  const parts = formatter.formatToParts(new Date());
  const lookup = (type) => parts.find((p) => p.type === type)?.value ?? '0';
  const pad = (num) => String(num).padStart(2, '0');

  const year = Number(lookup('year'));
  const month = Number(lookup('month'));
  const day = Number(lookup('day'));
  const hour = Number(lookup('hour'));
  const minute = Number(lookup('minute'));

  let base = new Date(Date.UTC(year, (month || 1) - 1, day || 1));
  const minutesSinceMidnight = hour * 60 + minute;
  if (minutesSinceMidnight < DAY_START_MINUTES) {
    base.setUTCDate(base.getUTCDate() - 1);
  }
  return `${base.getUTCFullYear()}-${pad(base.getUTCMonth() + 1)}-${pad(base.getUTCDate())}`;
}

export default function App() {
  const [days, setDays] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showPRTracker, setShowPRTracker] = useState(false);
  const [showSplitPlanner, setShowSplitPlanner] = useState(false);
  const [showEditSplitPage, setShowEditSplitPage] = useState(false);
  const [creatingDay, setCreatingDay] = useState(false);
  const [createDayError, setCreateDayError] = useState(null);

  const todayIso = getCurrentDayIso();
  const hasTodayEntry = days.some((day) => {
    if (!day?.log_date) return false;
    if (day.log_date.includes('T')) {
      return day.log_date.split('T')[0] === todayIso;
    }
    return day.log_date === todayIso;
  });

  const loadDays = async () => {
    try {
      const response = await fetch(`${API_BASE}/days`);
      const data = await response.json();

      console.log('Fetched days from API:', data.length, 'days');
      console.log('Today ISO:', todayIso);

      // Filter to show only today and days with completed workouts
      const filteredData = data.filter(day => {
        if (!day?.log_date) return false;

        // Extract date part for comparison
        const dayDate = day.log_date.includes('T')
          ? day.log_date.split('T')[0]
          : day.log_date;

        // Show if it's today
        const isToday = dayDate === todayIso;

        // Show if it has completed workouts
        const hasCompleted = day.completed_sets_count && day.completed_sets_count > 0;

        if (isToday || hasCompleted) {
          console.log(`Showing day ${dayDate}: isToday=${isToday}, completed=${day.completed_sets_count || 0}`);
        }

        return isToday || hasCompleted;
      });

      console.log('Filtered to', filteredData.length, 'days to display');

      // Update days and track last updated time
      setDays(prevDays => {
        const dataString = JSON.stringify(filteredData);
        const currentDataString = JSON.stringify(prevDays);

        if (dataString !== currentDataString) {
          setLastUpdated(new Date());
          return filteredData;
        }
        return prevDays;
      });

      setLoading(false);
    } catch (err) {
      console.error('Error loading days:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial load
    loadDays();
    
    // Set up polling every 5 seconds
    const interval = setInterval(loadDays, 5000);
    
    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, []);

  const refreshDays = () => {
    setLoading(true);
    loadDays();
  };

  const deleteDay = async (id) => {
    await fetch(`${API_BASE}/days/${id}`, { method: 'DELETE' });
    setDays(days.filter(d => d.id !== id));
    if (selected === id) setSelected(null);
  };

  const createTodayDay = async () => {
    if (creatingDay) return;
    setCreatingDay(true);
    setCreateDayError(null);
    try {
      const response = await fetch(`${API_BASE}/days`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: todayIso })
      });
      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || 'Failed to create day');
      }
      await loadDays();
    } catch (error) {
      console.error('Error creating today\'s day:', error);
      setCreateDayError(error.message || 'Unable to create today\'s entry.');
    } finally {
      setCreatingDay(false);
    }
  };

  const handleBack = () => {
    setShowPRTracker(false);
    setShowSplitPlanner(false);
    setShowEditSplitPage(false);
    setSelected(null);
    refreshDays(); // Refresh the list when going back
  };

  const handleEditSplit = () => {
    setShowEditSplitPage(true);
    setSelected(null);
    setShowPRTracker(false);
    setShowSplitPlanner(false);
  }

  const handlePRTracker = () => {
    setShowPRTracker(true);
    setSelected(null);
    setShowSplitPlanner(false);
  };

  const handleSplitPlanner = () => {
    setShowSplitPlanner(true);
    setShowPRTracker(false);
    setSelected(null);
  };

  // Styles
  const containerStyle = {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px'
  };

  const headerStyle = {
    borderBottom: '2px solid #eee',
    paddingBottom: '15px',
    marginBottom: '20px'
  };

  const titleStyle = {
    margin: 0,
    color: '#333',
    fontSize: '24px'
  };

  const loadingStyle = {
    textAlign: 'center',
    color: '#666',
    fontSize: '16px'
  };

  const emptyStateStyle = {
    textAlign: 'center',
    padding: '40px',
    border: '2px dashed #ddd',
    borderRadius: '8px',
    backgroundColor: '#f8f9fa'
  };

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    backgroundColor: 'white',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
  };

  const thStyle = {
    backgroundColor: '#f8f9fa',
    padding: '12px',
    textAlign: 'left',
    borderBottom: '2px solid #ddd',
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#333'
  };

  const tdStyle = {
    padding: '12px',
    borderBottom: '1px solid #eee',
    fontSize: '14px'
  };

  const buttonStyle = {
    padding: '6px 12px',
    margin: '0 4px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 'bold'
  };

  const viewButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#007bff',
    color: 'white'
  };



  const codeStyle = {
    backgroundColor: '#f8f9fa',
    padding: '2px 6px',
    borderRadius: '3px',
    fontSize: '13px',
    fontFamily: 'monospace'
  };

  const prButtonStyle = {
    padding: '8px 16px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold'
  };

  const splitButtonStyle = {
    padding: '8px 16px',
    backgroundColor: '#17a2b8',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
    marginLeft: '10px'
  };

  const createDayBannerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderRadius: '8px',
    border: '1px solid #ffe599',
    backgroundColor: '#fff8e1',
    marginBottom: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
  };

  const createDayButtonStyle = {
    padding: '10px 18px',
    backgroundColor: '#ff9800',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: creatingDay ? 'not-allowed' : 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
    opacity: creatingDay ? 0.7 : 1
  };

  const shouldShowCreateToday = !loading && !hasTodayEntry;

  const mainView = (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>🏋️ Workout Tracker</h1>
          {lastUpdated && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
        <div>
          <button style={prButtonStyle} onClick={handlePRTracker}>
            💪 View PRs
          </button>
          <button style={splitButtonStyle} onClick={handleEditSplit}>
            📅 Edit Split
          </button>
        </div>
      </div>

      {shouldShowCreateToday && (
        <div style={createDayBannerStyle}>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              No entry exists for today ({todayIso})
            </div>
            <div style={{ color: '#555' }}>
              Create a blank day so you can log workouts even without a split.
            </div>
            {createDayError && (
              <div style={{ color: '#c62828', marginTop: '6px', fontSize: '13px' }}>
                {createDayError}
              </div>
            )}
          </div>
          <button
            style={createDayButtonStyle}
            onClick={createTodayDay}
            disabled={creatingDay}
          >
            {creatingDay ? 'Creating…' : 'Create Today\'s Day'}
          </button>
        </div>
      )}
      
      {loading && (
        <div style={loadingStyle}>
          <p>Loading workout days...</p>
        </div>
      )}
      
      {!loading && days.length === 0 && !shouldShowCreateToday && (
        <div style={emptyStateStyle}>
          <h3>No workout history yet</h3>
          <p>You'll see days here once you complete some workouts.</p>
          <p>Create today's entry above to get started!</p>
        </div>
      )}
      
      {!loading && days.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>📅 Date</th>
              <th style={thStyle}>📝 Summary</th>
              <th style={thStyle}>⚡ Actions</th>
            </tr>
          </thead>
          <tbody>
            {days.map(d => (
              <tr key={d.id}>
                <td style={tdStyle}>
                  <strong>{format(parseISO(d.log_date), 'EEE, MMM d, yyyy')}</strong>
                </td>
                <td style={tdStyle}>
                  {d.summary ? (
                    <div style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {d.summary}
                    </div>
                  ) : (
                    <em style={{ color: '#666' }}>No summary</em>
                  )}
                </td>
                <td style={tdStyle}>
                  <button 
                    style={viewButtonStyle} 
                    onClick={() => setSelected(d.id)}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );

  return (
    <>
      <div style={containerStyle}>
        {showEditSplitPage ? (
          <EditSplitPage onBack={handleBack} />
        ) : showSplitPlanner ? (
          <SplitPlanner onBack={handleBack} />
        ) : showPRTracker ? (
          <PRTracker onBack={handleBack} />
        ) : selected ? (
          <DayDetail id={selected} onBack={handleBack} onDelete={deleteDay} />
        ) : (
          mainView
        )}
      </div>
    </>
  );
}
