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
        Schema::create('m_l_labels', function (Blueprint $table) {
            $table->id();
            $table->foreignId('ping_record_id')->constrained('ping_records')->onDelete('cascade');
            $table->string('label')->comment('Classification label for training data');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('m_l_labels');
    }
};
