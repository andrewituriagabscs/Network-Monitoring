<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('m_l_models', function (Blueprint $table) {
            $table->id();
            $table->string('model_type')->comment('Type of ML model (random_forest, neural_net, etc.)');
            $table->string('status')->default('inactive')->comment('active, inactive, training');
            $table->string('version')->default('1.0')->comment('Version of the model');
            $table->integer('accuracy')->nullable()->comment('Model accuracy percentage');
            $table->timestamp('trained_at')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('m_l_models');
    }
};
