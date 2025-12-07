import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

const LOG_FILE = path.join(process.cwd(), '..', 'server_state', 'agent_log.txt');

export async function GET() {
    try {
        if (!fs.existsSync(LOG_FILE)) {
            return NextResponse.json({ logs: [], error: 'Log file not found' });
        }

        const content = fs.readFileSync(LOG_FILE, 'utf8');
        const lines = content.split('\n').filter(line => line.trim());

        // Return last 100 lines, most recent first
        const recentLogs = lines.slice(-100).reverse();

        return NextResponse.json({
            logs: recentLogs,
            total: lines.length,
            showing: Math.min(100, lines.length)
        });
    } catch (error) {
        return NextResponse.json({ logs: [], error: String(error) }, { status: 500 });
    }
}
