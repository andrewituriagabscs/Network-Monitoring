@extends('layout')

@section('title', 'Ping Records')

@section('content')
    <div class="heading-row">
        <div>
            <p class="eyebrow">ICMP history</p>
            <h1>Ping Records</h1>
            <p class="subtitle">Saved latency and packet-loss samples for analysis.</p>
        </div>
    </div>

    <div class="panel">
        <div class="toolbar">
            <span class="pill">1 hour</span>
            <span class="pill">24 hours</span>
            <span class="pill">7 days</span>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Device</th>
                        <th>Target</th>
                        <th>Loss</th>
                        <th>Min</th>
                        <th>Median</th>
                        <th>Max</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse ($records as $record)
                        <tr>
                            <td>{{ $record->recorded_at?->format('M d, H:i') ?? 'N/A' }}</td>
                            <td>{{ $record->device?->name ?? 'Unknown' }}</td>
                            <td>{{ $record->device?->target ?? '—' }}</td>
                            <td>{{ $record->packet_loss ?? 0 }}%</td>
                            <td>{{ $record->latency_min ?? '—' }}</td>
                            <td>{{ $record->latency_median ?? '—' }}</td>
                            <td>{{ $record->latency_max ?? '—' }}</td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="7">No ping records yet.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
        {{ $records->links() }}
    </div>
@endsection
