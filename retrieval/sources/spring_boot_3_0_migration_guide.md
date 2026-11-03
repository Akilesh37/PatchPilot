# Spring Boot 3.0 Migration Guide

Canonical URL: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide
Target Version: Spring Boot 3.0+
Source Baseline: Spring Boot 2.7.x
Provenance: Official Spring Boot Wiki

## Upgrading from Spring Boot 2.x
Spring Boot 3.0 requires Java 17 as a minimum version. If you are currently using Java 8 or Java 11, you must upgrade your JDK before migrating your application to Spring Boot 3.0.

## Jakarta EE Migration
Spring Boot 3.0 has upgraded from Java EE 8 to Jakarta EE 9 APIs and provides dependencies for Jakarta EE 10.
Wherever possible, EE APIs have been upgraded to their Jakarta equivalent. This requires changing package names from `javax.*` to `jakarta.*`:

- `javax.persistence.*` -> `jakarta.persistence.*` (e.g. `@Entity`, `@Id`, `@GeneratedValue`, `@Column`, `@Table`)
- `javax.servlet.*` -> `jakarta.servlet.*` (e.g. `HttpServletRequest`, `HttpServletResponse`, `Filter`)
- `javax.validation.*` -> `jakarta.validation.*` (e.g. `@NotNull`, `@NotBlank`, `@Size`, `@Valid`)
- `javax.annotation.*` -> `jakarta.annotation.*` (e.g. `@PostConstruct`, `@PreDestroy`)
- `javax.transaction.*` -> `jakarta.transaction.*`

Do not migrate `javax.sql.*` or `javax.crypto.*` as these are part of the Java SE standard library.

## Configuration Properties Changes
Several configuration properties have been relocated or renamed:
- `spring.redis.*` properties have moved to `spring.data.redis.*` (e.g. `spring.data.redis.host`, `spring.data.redis.port`).
- `server.max-http-header-size` has been renamed to `server.max-http-request-header-size`.
- `spring.jpa.hibernate.naming.implicit-strategy` changed defaults to SpringImplicitNamingStrategy.
