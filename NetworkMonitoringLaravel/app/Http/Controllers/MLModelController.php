<?php

namespace App\Http\Controllers;

use App\Models\MLLabel;
use App\Models\MLModel;
use App\Models\PingRecord;

class MLModelController extends Controller
{
    public function index()
    {
        $models = MLModel::latest()->get();
        $validSamples = PingRecord::count();
        $labeledSamples = MLLabel::count();
        $latestModel = MLModel::latest()->first();

        return view('ml-insights', compact('models', 'validSamples', 'labeledSamples', 'latestModel'));
    }
}
