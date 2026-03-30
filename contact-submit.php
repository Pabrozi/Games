<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'message' => 'Metodo nao permitido.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$rawInput = file_get_contents('php://input');
$payload = [];

if ($rawInput !== false && trim($rawInput) !== '') {
    $decoded = json_decode($rawInput, true);
    if (is_array($decoded)) {
        $payload = $decoded;
    }
}

if (!$payload) {
    $payload = $_POST;
}

$name = trim((string)($payload['name'] ?? ''));
$email = trim((string)($payload['email'] ?? ''));
$subject = trim((string)($payload['subject'] ?? ''));
$message = trim((string)($payload['message'] ?? ''));
$website = trim((string)($payload['website'] ?? ''));

if ($website !== '') {
    echo json_encode([
        'success' => true,
        'message' => 'Mensagem recebida.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($name === '' || $email === '' || $subject === '' || $message === '') {
    http_response_code(422);
    echo json_encode([
        'success' => false,
        'message' => 'Preencha todos os campos obrigatorios.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(422);
    echo json_encode([
        'success' => false,
        'message' => 'Informe um email valido.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$storageDir = __DIR__ . DIRECTORY_SEPARATOR . 'data' . DIRECTORY_SEPARATOR . 'contact-submissions';
if (!is_dir($storageDir) && !mkdir($storageDir, 0775, true) && !is_dir($storageDir)) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Nao foi possivel preparar o armazenamento da mensagem.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$timestamp = gmdate('Ymd_His');
$random = bin2hex(random_bytes(4));
$filename = $storageDir . DIRECTORY_SEPARATOR . $timestamp . '_' . $random . '.json';

$record = [
    'name' => $name,
    'email' => $email,
    'subject' => $subject,
    'message' => $message,
    'ip' => $_SERVER['REMOTE_ADDR'] ?? '',
    'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? '',
    'created_at_utc' => gmdate(DATE_ATOM),
];

$written = file_put_contents($filename, json_encode($record, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
if ($written === false) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Nao foi possivel salvar a mensagem no servidor.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

echo json_encode([
    'success' => true,
    'message' => 'Recebemos sua mensagem e vamos analisar o contato em breve.',
], JSON_UNESCAPED_UNICODE);
