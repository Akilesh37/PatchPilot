# Spring Security 6.0 Migration Guide

Canonical URL: https://docs.spring.io/spring-security/reference/5.8/migration/index.html
Target Version: Spring Security 6.0+ (Spring Boot 3.0+)
Source Baseline: Spring Security 5.x
Provenance: Official Spring Security Documentation

## Removal of WebSecurityConfigurerAdapter
In Spring Security 5.7, `WebSecurityConfigurerAdapter` was deprecated. In Spring Security 6.0 and Spring Boot 3.0, `WebSecurityConfigurerAdapter` has been removed completely.
Applications must now register a `SecurityFilterChain` bean instead:

```java
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/public/**").permitAll()
            .anyRequest().authenticated()
        );
    return http.build();
}
```

## DSL Migration from authorizeRequests() to authorizeHttpRequests()
The `authorizeRequests()` method is deprecated and replaced by `authorizeHttpRequests()`.
Additionally, URL ant matchers have changed:
- `antMatchers("/api/**")` is replaced with `requestMatchers("/api/**")`.
- `mvcMatchers("/api/**")` is replaced with `requestMatchers("/api/**")`.
