import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const CONTEXT_FILE = path.join(process.cwd(), '../context.md');

export async function GET() {
    try {
        if (!fs.existsSync(CONTEXT_FILE)) {
            return NextResponse.json({ content: 'Context file not found.' });
        }
        const content = fs.readFileSync(CONTEXT_FILE, 'utf8');
        return NextResponse.json({ content });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to read context' }, { status: 500 });
    }
}
