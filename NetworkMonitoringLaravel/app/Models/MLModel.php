<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class MLModel extends Model
{
    protected $table = 'm_l_models';

    protected $fillable = ['model_type', 'status', 'version', 'accuracy', 'trained_at'];

    protected $casts = [
        'accuracy' => 'integer',
        'trained_at' => 'datetime',
    ];
}
