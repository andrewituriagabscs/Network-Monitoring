<?php

namespace App\Http\Controllers;

use App\Models\Alert;

class AlertController extends Controller
{
    public function index()
    {
        $alerts = Alert::with('device')->latest()->paginate(15);
        $criticalCount = Alert::where('severity', 'critical')->count();
        $warningCount = Alert::where('severity', 'warning')->count();

        return view('alerts', compact('alerts', 'criticalCount', 'warningCount'));
    }
}
