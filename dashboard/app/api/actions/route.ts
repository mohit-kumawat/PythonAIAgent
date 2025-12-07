import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const ACTIONS_FILE = path.join(process.cwd(), '../server_state/pending_actions.json');

export async function GET() {
    try {
        if (!fs.existsSync(ACTIONS_FILE)) {
            return NextResponse.json([]);
        }
        const data = fs.readFileSync(ACTIONS_FILE, 'utf8');
        return NextResponse.json(JSON.parse(data));
    } catch (error) {
        return NextResponse.json({ error: 'Failed to read actions' }, { status: 500 });
    }
}

export async function POST(request: Request) {
    try {
        const { id, action } = await request.json(); // action = 'APPROVE' | 'REJECT'

        if (!fs.existsSync(ACTIONS_FILE)) {
            return NextResponse.json({ error: 'File not found' }, { status: 404 });
        }

        const data = JSON.parse(fs.readFileSync(ACTIONS_FILE, 'utf8'));
        const updated = data.map((item: any) => {
            if (item.id === id) {
                return {
                    ...item,
                    status: action === 'APPROVE' ? 'APPROVED' : 'REJECTED'
                };
            }
            return item;
        });

        fs.writeFileSync(ACTIONS_FILE, JSON.stringify(updated, null, 2));
        return NextResponse.json({ success: true });

    } catch (error) {
        return NextResponse.json({ error: 'Failed to update action' }, { status: 500 });
    }
}
