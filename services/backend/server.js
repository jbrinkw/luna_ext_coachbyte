const express = require('express');
const cors = require('cors');
const path = require('path');

// Load env from extension root (2 levels up from this file)
const repoRoot = path.resolve(__dirname, '..', '..');
require('dotenv').config({ path: path.join(repoRoot, '.env') });

const db = require('./db');

const app = express();
console.log('[CoachByte Backend] Starting...');
app.use(cors());
app.use(express.json());

// Support proxies that strip the /api prefix (some deployments route /api/coachbyte to this service)
app.use((req, res, next) => {
  const resetUrl = (newUrl) => {
    req.url = newUrl;
    req._parsedUrl = undefined;
  };

  if (req.path.startsWith('/api/coachbyte/')) {
    resetUrl(`/api${req.url.slice('/api/coachbyte'.length)}`);
  } else if (!req.path.startsWith('/api/')) {
    const suffix = req.url.startsWith('/') ? req.url : `/${req.url}`;
    resetUrl(`/api${suffix}`);
  }
  next();
});

// Initialize database tables on startup (idempotent)
(async () => {
  try {
    await db.initDb(false);
    await db.ensureTodayPlan();
    console.log('[CoachByte Backend] Database initialized and today ensured');
  } catch (e) {
    console.error('[CoachByte Backend] Startup DB init failed:', e);
  }
})();

app.get('/api/days', async (req, res) => {
  try {
    await db.ensureTodayPlan();
    const days = await db.getAllDays();
    res.json(days);
  } catch (error) {
    console.error('Error getting days:', error);
    res.status(500).json({ error: 'Failed to get days' });
  }
});

app.post('/api/days', async (req, res) => {
  try {
    const { date } = req.body;
    const id = await db.ensureDay(date);
    res.json({ id });
  } catch (error) {
    console.error('Error creating day:', error);
    res.status(500).json({ error: 'Failed to create day' });
  }
});

app.delete('/api/days/:id', async (req, res) => {
  try {
    await db.deleteDay(req.params.id);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting day:', error);
    res.status(500).json({ error: 'Failed to delete day' });
  }
});

app.get('/api/days/:id', async (req, res) => {
  try {
    const data = await db.getDay(req.params.id);
    if (!data) return res.status(404).end();
    res.json(data);
  } catch (error) {
    console.error('Error getting day:', error);
    res.status(500).json({ error: 'Failed to get day' });
  }
});

// Split (weekly plan) endpoints
app.get('/api/split', async (req, res) => {
  try {
    const split = await db.getAllSplit();
    res.json(split);
  } catch (error) {
    console.error('Error getting split:', error);
    res.status(500).json({ error: 'Failed to get split' });
  }
});

// Split notes endpoints
app.get('/api/split/notes', async (req, res) => {
  try {
    const notes = await db.getSplitNotes();
    res.json(notes);
  } catch (error) {
    console.error('Error getting split notes:', error);
    res.status(500).json({ error: 'Failed to get split notes' });
  }
});

app.put('/api/split/notes', async (req, res) => {
  try {
    const { notes } = req.body || {};
    await db.setSplitNotes(String(notes || ''));
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating split notes:', error);
    res.status(500).json({ error: 'Failed to update split notes' });
  }
});

app.get('/api/split/:day', async (req, res) => {
  try {
    const items = await db.getSplit(Number(req.params.day));
    res.json(items);
  } catch (error) {
    console.error('Error getting split day:', error);
    res.status(500).json({ error: 'Failed to get split day' });
  }
});

app.post('/api/split/:day', async (req, res) => {
  try {
    const id = await db.addSplit(Number(req.params.day), req.body);
    res.json({ id });
  } catch (error) {
    console.error('Error adding split set:', error);
    res.status(500).json({ error: 'Failed to add split set' });
  }
});

app.put('/api/split/plan/:id', async (req, res) => {
  try {
    await db.updateSplit(Number(req.params.id), req.body);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating split set:', error);
    res.status(500).json({ error: 'Failed to update split set' });
  }
});

app.delete('/api/split/plan/:id', async (req, res) => {
  try {
    await db.deleteSplit(Number(req.params.id));
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting split set:', error);
    res.status(500).json({ error: 'Failed to delete split set' });
  }
});

app.post('/api/days/:id/plan', async (req, res) => {
  try {
    const id = await db.addPlan(req.params.id, req.body);
    res.json({ id });
  } catch (error) {
    console.error('Error adding plan:', error);
    res.status(500).json({ error: 'Failed to add plan' });
  }
});

app.put('/api/plan/:id', async (req, res) => {
  try {
    await db.updatePlan(Number(req.params.id), req.body);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating plan:', error);
    res.status(500).json({ error: 'Failed to update plan' });
  }
});

app.delete('/api/plan/:id', async (req, res) => {
  try {
    await db.deletePlan(Number(req.params.id));
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting plan:', error);
    res.status(500).json({ error: 'Failed to delete plan' });
  }
});

app.post('/api/days/:id/completed', async (req, res) => {
  try {
    // Get the current plan to find the rest time for the next set
    const dayData = await db.getDay(req.params.id);
    const nextSet = dayData.plan.length > 0 ? dayData.plan[0] : null;
    
    const id = await db.addCompleted(req.params.id, req.body);
    
    // If there was a next set, set a timer for its rest period
    if (nextSet && nextSet.rest) {
      try {
        const restSeconds = nextSet.rest; // Use exact seconds
        await db.setTimerSeconds(restSeconds);
      } catch (timerError) {
        console.error('Error setting timer:', timerError);
        // Don't fail the main request if timer setting fails
      }
    }
    
    // Return the complete data including timestamp
    const updatedDayData = await db.getDay(req.params.id);
    const completedSet = updatedDayData.completed.find(c => c.id === id);
    
    if (completedSet) {
      res.json({
        id: completedSet.id,
        exercise: completedSet.exercise,
        reps_done: completedSet.reps_done,
        load_done: completedSet.load_done,
        completed_at: completedSet.completed_at
      });
    } else {
      res.json({ id });
    }
  } catch (error) {
    console.error('Error adding completed set:', error);
    res.status(500).json({ error: 'Failed to add completed set' });
  }
});

app.put('/api/completed/:id', async (req, res) => {
  try {
    await db.updateCompleted(Number(req.params.id), req.body);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating completed set:', error);
    res.status(500).json({ error: 'Failed to update completed set' });
  }
});

app.delete('/api/completed/:id', async (req, res) => {
  try {
    await db.deleteCompleted(Number(req.params.id));
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting completed set:', error);
    res.status(500).json({ error: 'Failed to delete completed set' });
  }
});

app.put('/api/days/:id/summary', async (req, res) => {
  try {
    await db.updateSummary(req.params.id, req.body.summary || '');
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating summary:', error);
    res.status(500).json({ error: 'Failed to update summary' });
  }
});

// PR tracking endpoint
app.get('/api/prs', async (req, res) => {
  try {
    const prs = await db.getPRs();
    res.json(prs);
  } catch (error) {
    console.error('Error getting PRs:', error);
    res.status(500).json({ error: 'Failed to get PRs' });
  }
});

// CRUD endpoints for tracked PRs
app.get('/api/tracked-prs', async (req, res) => {
  try {
    const prs = await db.getTrackedPRs();
    res.json(prs);
  } catch (error) {
    console.error('Error getting tracked PRs:', error);
    res.status(500).json({ error: 'Failed to get tracked PRs' });
  }
});

app.put('/api/tracked-prs', async (req, res) => {
  try {
    const { exercise, reps, maxLoad } = req.body;
    await db.upsertTrackedPR(exercise, reps, maxLoad);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating tracked PR:', error);
    res.status(500).json({ error: 'Failed to update tracked PR' });
  }
});

app.delete('/api/tracked-prs', async (req, res) => {
  try {
    const { exercise, reps } = req.body;
    await db.deleteTrackedPR(exercise, reps);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting tracked PR:', error);
    res.status(500).json({ error: 'Failed to delete tracked PR' });
  }
});

// CRUD endpoints for tracked exercises (exercise names only)
app.get('/api/tracked-exercises', async (req, res) => {
  try {
    const exercises = await db.getTrackedExercises();
    res.json(exercises);
  } catch (error) {
    console.error('Error getting tracked exercises:', error);
    res.status(500).json({ error: 'Failed to get tracked exercises' });
  }
});

app.post('/api/tracked-exercises', async (req, res) => {
  try {
    const { exercise } = req.body;
    await db.addTrackedExercise(exercise);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error adding tracked exercise:', error);
    res.status(500).json({ error: 'Failed to add tracked exercise' });
  }
});

app.delete('/api/tracked-exercises', async (req, res) => {
  try {
    const { exercise } = req.body;
    await db.removeTrackedExercise(exercise);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error removing tracked exercise:', error);
    res.status(500).json({ error: 'Failed to remove tracked exercise' });
  }
});

// Get timer status endpoint
app.get('/api/timer', async (req, res) => {
  try {
    const t = await db.getTimerStatus();
    let status = 'no_timer';
    if (t && typeof t.remainingSeconds === 'number') {
      status = t.remainingSeconds > 0 ? 'running' : 'expired';
    }
    res.json({
      status,
      remaining_seconds: Math.max(0, (t && t.remainingSeconds) || 0),
      ends_at: t && t.endsAt ? t.endsAt : null,
    });
  } catch (error) {
    console.error('Error getting timer status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

const PORT = process.env.PORT || 5300;
const HOST = '127.0.0.1';

app.listen(PORT, HOST, () => {
  console.log(`[CoachByte Backend] Server running on http://${HOST}:${PORT}`);
});
