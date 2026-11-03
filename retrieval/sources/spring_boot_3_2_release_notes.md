# Spring Boot 3.2 Release Notes and Migration Guide

Canonical URL: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Release-Notes
Target Version: Spring Boot 3.2.x
Source Baseline: Spring Boot 3.1.x / 3.0.x
Provenance: Official Spring Boot Release Engineering

## Upgrading to Spring Boot 3.2
Spring Boot 3.2 builds on Spring Framework 6.1 and requires Java 17 as the baseline, with official support for Java 21.
Virtual threads (Project Loom) can be enabled via `spring.threads.virtual.enabled=true`.

## RestClient and HTTP Interfaces
Spring Boot 3.2 introduces the synchronous `RestClient` abstraction alongside the reactive `WebClient`.
`RestTemplate` remains in maintenance mode but is supported.

## Observability and Micrometer 1.12
Tracing and metrics under Micrometer have been enhanced. Actuator endpoints expose standardized health and metric formats.
Property deprecations from 3.0 continue to be enforced in 3.2.

