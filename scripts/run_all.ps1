# Reproduce all reported results from cached API responses and local verifiers.
# Usage: .\scripts\run_all.ps1 [-RerunVerifiers]
param (
    [switch]$RerunVerifiers
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

$Config = "configs/config.yaml"

Write-Host "=== Hallucination Verifier C - Full Pipeline Reproduction ==="
Write-Host "Config: $Config"
Write-Host ""

if ($RerunVerifiers) {
    Write-Host "--- Re-running local verifiers on test and RAG splits ---"
    python -m src.run_verifiers --config $Config --split test --verifier filter_b
    python -m src.run_verifiers --config $Config --split test --verifier rouge
    python -m src.run_verifiers --config $Config --split rag --verifier filter_b
    python -m src.run_verifiers --config $Config --split rag --verifier rouge
}

Write-Host "--- 1. Evaluating Experiment 1 (MedHallu test, n=400) ---"
python -m src.evaluate --config $Config --exp exp1

Write-Host "--- 2. Evaluating Experiment 2 (PubMedQA RAG, n=200) ---"
python -m src.evaluate --config $Config --exp exp2

Write-Host "--- 3. Running Cross-Experiment Synthesis ---"
python -m src.cross_experiment --config $Config

Write-Host "--- 4. Generating Publication Figures (PNG and PDF) ---"
python -m src.figures --config $Config

Write-Host "--- 5. Exporting Numbers of Record for Documentation ---"
python -m src.site_export

Write-Host ""
Write-Host "=== Full reproduction completed successfully! ==="
