# Jakarta EE 10 Specification & Migration Reference

Canonical URL: https://jakarta.ee/specifications/platform/10/
Target Version: Spring Boot 3.0+ (Jakarta EE 10)
Source Baseline: Java EE 8 (Spring Boot 2.x)
Provenance: Eclipse Foundation Jakarta EE 10 Release Specification

## Jakarta Persistence 3.1
Jakarta Persistence 3.1 is the default persistence specification in Spring Boot 3.x and Hibernate 6.x.
Namespace changes:
- All classes in package `javax.persistence` moved to package `jakarta.persistence`.
- Key annotations: `@Entity`, `@Table`, `@Id`, `@GeneratedValue`, `@Column`, `@ManyToOne`, `@OneToMany`.
- EntityManager API: `jakarta.persistence.EntityManager`, `jakarta.persistence.PersistenceContext`.

## Jakarta Servlet 6.0
Jakarta Servlet 6.0 replaces Servlet 4.0 (javax.servlet):
- `javax.servlet.http.HttpServletRequest` -> `jakarta.servlet.http.HttpServletRequest`
- `javax.servlet.http.HttpServletResponse` -> `jakarta.servlet.http.HttpServletResponse`
- `javax.servlet.Filter` -> `jakarta.servlet.Filter`
- Deprecated methods from Servlet 4.0 (like `request.getRealPath()`) have been removed completely.

## Jakarta Validation 3.0
Jakarta Bean Validation 3.0 replaces `javax.validation`:
- Annotations: `@NotNull`, `@Size`, `@Valid`, `@Min`, `@Max`, `@Email`.
- Validator interface: `jakarta.validation.Validator`.
- Hibernate Validator 8.x is the reference implementation for Jakarta Validation 3.0.

