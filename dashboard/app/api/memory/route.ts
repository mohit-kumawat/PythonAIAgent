import { NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import * as path from 'path';
import * as fs from 'fs';

const DB_PATH = path.join(process.cwd(), '..', 'memory', 'pm_agent.db');

export async function GET(request: Request) {
    try {
        const { searchParams } = new URL(request.url);
        const category = searchParams.get('category');
        const query = searchParams.get('query');
        const limit = parseInt(searchParams.get('limit') || '20');

        // Check if database exists
        if (!fs.existsSync(DB_PATH)) {
            return NextResponse.json({
                entries: [],
                stats: { decisions: 0, threads: 0, knowledge: 0, actions: 0 },
                error: 'Memory database not initialized yet'
            });
        }

        const db = new Database(DB_PATH, { readonly: true });

        // Get stats
        const decisionsCount = db.prepare('SELECT COUNT(*) as count FROM decisions').get() as any;
        const threadsCount = db.prepare('SELECT COUNT(*) as count FROM thread_context').get() as any;
        const knowledgeCount = db.prepare('SELECT COUNT(*) as count FROM knowledge').get() as any;
        const actionsCount = db.prepare('SELECT COUNT(*) as count FROM action_history').get() as any;

        const stats = {
            decisions: decisionsCount?.count || 0,
            threads: threadsCount?.count || 0,
            knowledge: knowledgeCount?.count || 0,
            actions: actionsCount?.count || 0
        };

        // Get knowledge entries
        let entries: any[] = [];

        if (query) {
            if (category) {
                entries = db.prepare(`
          SELECT * FROM knowledge 
          WHERE category = ? AND content LIKE ?
          ORDER BY created_at DESC LIMIT ?
        `).all(category, `%${query}%`, limit);
            } else {
                entries = db.prepare(`
          SELECT * FROM knowledge 
          WHERE content LIKE ?
          ORDER BY created_at DESC LIMIT ?
        `).all(`%${query}%`, limit);
            }
        } else if (category) {
            entries = db.prepare(`
        SELECT * FROM knowledge 
        WHERE category = ?
        ORDER BY created_at DESC LIMIT ?
      `).all(category, limit);
        } else {
            entries = db.prepare(`
        SELECT * FROM knowledge 
        ORDER BY created_at DESC LIMIT ?
      `).all(limit);
        }

        db.close();

        return NextResponse.json({
            entries,
            stats
        });

    } catch (error) {
        console.error('Memory API error:', error);
        return NextResponse.json({
            entries: [],
            stats: { decisions: 0, threads: 0, knowledge: 0, actions: 0 },
            error: String(error)
        }, { status: 500 });
    }
}
