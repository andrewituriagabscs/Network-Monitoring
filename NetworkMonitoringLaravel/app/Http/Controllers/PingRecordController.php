<?php

namespace App\Http\Controllers;

use App\Models\PingRecord;

class PingRecordController extends Controller
{
    public function index()
    {
        $records = PingRecord::with('device')->latest('recorded_at')->paginate(20);

        return view('ping-records', compact('records'));
    }
}
