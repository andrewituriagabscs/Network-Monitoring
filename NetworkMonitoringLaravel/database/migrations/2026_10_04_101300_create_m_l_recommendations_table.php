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
        Schema::create('m_l_recommendations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('monitored_device_id')->constrained('monitored_devices')->onDelete('cascade');
            $table->text('recommendation')->comment('ML-generated recommendation for device');
            $table->string('priority')->default('medium')->comment('low, medium, high, critical');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('m_l_recommendations');
    }
};
