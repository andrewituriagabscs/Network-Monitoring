@extends('layout')

@section('title', 'ML Insights')

@section('content')
    <div class="heading-row">
        <div>
            <p class="eyebrow">Model readiness</p>
            <h1>ML Insights</h1>
            <p class="subtitle">Review model status and training readiness.</p>
        </div>
        <a href="{{ route('monitor.index') }}" class="btn warning">Train model</a>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <h3>Valid samples</h3>
            <div class="stat-value">{{ $validSamples }}</div>
        </div>
        <div class="stat-card">
            <h3>Labeled samples</h3>
            <div class="stat-value">{{ $labeledSamples }}</div>
        </div>
        <div class="stat-card">
            <h3>Latest model</h3>
            <div class="stat-value">{{ $latestModel?->model_type ?? 'Not trained' }}</div>
        </div>
    </div>

    <div class="panel">
        <h2>Model library</h2>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Status</th>
                        <th>Version</th>
                        <th>Accuracy</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse ($models as $model)
                        <tr>
                            <td>{{ $model->model_type }}</td>
                            <td><span class="badge {{ $model->status === 'active' ? 'success' : 'secondary' }}">{{ ucfirst($model->status) }}</span></td>
                            <td>{{ $model->version }}</td>
                            <td>{{ $model->accuracy ? $model->accuracy.'%' : '—' }}</td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="4">No models have been trained yet.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>
@endsection
