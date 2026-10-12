<?php

namespace App\Http\Controllers;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Symfony\Component\HttpFoundation\Response;

class PythonApiController extends Controller
{
    public function forward(Request $request, string $path): Response
    {
        $baseUrl = rtrim((string) config('services.python_monitoring.url'), '/');
        $pendingRequest = Http::connectTimeout(3)
            ->timeout(180)
            ->accept($request->header('Accept', 'application/json'));

        if ($request->getContent() !== '') {
            $pendingRequest = $pendingRequest->withBody(
                $request->getContent(),
                $request->header('Content-Type', 'application/json')
            );
        }

        try {
            $upstream = $pendingRequest->send(
                $request->method(),
                $baseUrl.'/api/'.$path,
                ['query' => $request->query()]
            );
        } catch (ConnectionException) {
            return response()->json([
                'error' => 'Python monitoring service is unavailable.',
            ], 503);
        }

        $headers = [];
        foreach (['content-type', 'content-disposition', 'cache-control'] as $header) {
            $value = $upstream->header($header);
            if ($value !== null) {
                $headers[$header] = $value;
            }
        }

        return response($upstream->body(), $upstream->status(), $headers);
    }
}
