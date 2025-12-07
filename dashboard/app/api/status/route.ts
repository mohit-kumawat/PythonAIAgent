import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const STATUS_FILE = path.join(process.cwd(), '../server_state/status.json');

export async function GET() {
    try {
        if (!fs.existsSync(STATUS_FILE)) {
            return NextResponse.json({ status: 'OFFLINE', detail: 'State file not found' });
        }
        const data = fs.readFileSync(STATUS_FILE, 'utf8');
        return NextResponse.json(JSON.parse(data));
    } catch (error) {
        return NextResponse.json({ error: 'Failed to read status' }, { status: 500 });
    }
}
