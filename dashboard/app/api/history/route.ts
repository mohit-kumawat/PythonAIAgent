import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

const PENDING_ACTIONS_FILE = path.join(process.cwd(), '..', 'server_state', 'pending_actions.json');

export async function GET(request: Request) {
    try {
        const { searchParams } = new URL(request.url);
        const status = searchParams.get('status');
        const limit = parseInt(searchParams.get('limit') || '50');

        if (!fs.existsSync(PENDING_ACTIONS_FILE)) {
            return NextResponse.json([]);
        }

        const content = fs.readFileSync(PENDING_ACTIONS_FILE, 'utf8');
        if (!content.trim()) {
            return NextResponse.json([]);
        }

        let actions = JSON.parse(content);

        // Filter by status if specified
        if (status) {
            if (status === 'COMPLETED') {
                // Show both EXECUTED and REJECTED_LOGGED for history
                actions = actions.filter((a: any) =>
                    a.status === 'EXECUTED' || a.status === 'REJECTED_LOGGED' || a.status === 'REJECTED' || a.status === 'FAILED'
                );
            } else if (status === 'PENDING') {
                actions = actions.filter((a: any) => a.status === 'PENDING');
            } else {
                actions = actions.filter((a: any) => a.status === status);
            }
        }

        // Sort by created_at descending (most recent first)
        actions.sort((a: any, b: any) => {
            const dateA = new Date(a.created_at || 0).getTime();
            const dateB = new Date(b.created_at || 0).getTime();
            return dateB - dateA;
        });

        // Limit results
        actions = actions.slice(0, limit);

        return NextResponse.json(actions);
    } catch (error) {
        return NextResponse.json([], { status: 500 });
    }
}
