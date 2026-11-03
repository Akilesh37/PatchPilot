# Spring Boot 2.7 Release Baseline Reference

Canonical URL: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.7-Release-Notes
Target Version: Spring Boot 2.7.x
Source Baseline: Spring Boot 2.6.x
Provenance: Official Spring Boot Documentation

## Java Baseline in Spring Boot 2.7
Spring Boot 2.7 supports Java 8, Java 11, and Java 17. The default build baseline remains Java 8.
Applications can use Java 8 language level constructs with `javax.*` EE packages.

## Auto-Configuration Registration in 2.7
In Spring Boot 2.7, new auto-configuration classes should be registered in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`.
The legacy `META-INF/spring.factories` registration continues to be supported in 2.7 for backward compatibility, but is deprecated for Spring Boot 3.0.

## Spring Security 5.7 Integration
Spring Boot 2.7 uses Spring Security 5.7. In this version, `WebSecurityConfigurerAdapter` is marked as `@Deprecated`, but still functional.
Applications are encouraged to start adopting `SecurityFilterChain` beans before migrating to Spring Boot 3.0.

