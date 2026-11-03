package tools;

import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.tools.*;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.*;

/**
 * Production JDK-based AST Parser for Java 17+ source files.
 * Uses the official JDK Compiler Tree API (JavacTask).
 * Features:
 * - Package and import analysis
 * - Class, interface, record, enum, method, field, and annotation detection
 * - Deprecated Spring Security 5 and Spring Framework API detection
 * - Java language level compatibility analysis (records, pattern matching, switch expressions, text blocks, sealed classes)
 * - Deep migration site localization across imports, annotations, field declarations, and method calls
 */
public class JavaAstParser {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java tools.JavaAstParser <path-to-java-file>");
            System.exit(1);
        }

        File file = new File(args[0]);
        if (!file.exists()) {
            System.err.println("File does not exist: " + file.getAbsolutePath());
            System.exit(1);
        }

        try {
            String source = Files.readString(file.toPath());
            String jsonOutput = parseJavaSource(file.getPath(), source);
            System.out.println(jsonOutput);
        } catch (Exception e) {
            System.err.println("Error parsing file " + file.getPath() + ": " + e.getMessage());
            e.printStackTrace();
            System.exit(2);
        }
    }

    public static String parseJavaSource(String filePath, String source) throws IOException {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("JDK JavaCompiler not available in current runtime environment.");
        }

        StandardJavaFileManager fileManager = compiler.getStandardFileManager(null, null, null);
        SimpleJavaFileObject fileObject = new SimpleJavaFileObject(
            new File(filePath).toURI(),
            JavaFileObject.Kind.SOURCE
        ) {
            @Override
            public CharSequence getCharContent(boolean ignoreEncodingErrors) {
                return source;
            }
        };

        // Parse with source level 17
        List<String> options = List.of("--release", "17");
        JavacTask task = (JavacTask) compiler.getTask(null, fileManager, null, options, null, List.of(fileObject));
        SourcePositions positions = Trees.instance(task).getSourcePositions();

        Iterable<? extends CompilationUnitTree> asts = task.parse();
        CompilationUnitTree cu = asts.iterator().next();

        String[] lines = source.split("\\r?\\n");

        List<String> imports = new ArrayList<>();
        List<String> types = new ArrayList<>();
        List<String> interfaces = new ArrayList<>();
        List<String> methods = new ArrayList<>();
        List<String> fields = new ArrayList<>();
        List<String> annotations = new ArrayList<>();
        List<String> modernFeatures = new ArrayList<>();
        List<String> deprecatedSpringApis = new ArrayList<>();
        List<Map<String, Object>> migrationSites = new ArrayList<>();

        // 1. Analyze Imports
        for (ImportTree imp : cu.getImports()) {
            String impStr = imp.getQualifiedIdentifier().toString();
            imports.add(impStr);

            long startPos = positions.getStartPosition(cu, imp);
            int lineNum = (int) cu.getLineMap().getLineNumber(startPos);
            String lineContent = (lineNum <= lines.length && lineNum > 0) ? lines[lineNum - 1].trim() : impStr;

            if (impStr.startsWith("javax.persistence.")) {
                addSite(migrationSites, filePath, lineNum, "RULE-JAKARTA-EE-PERSISTENCE", "javax.persistence.", lineContent, "confirmed");
            } else if (impStr.startsWith("javax.servlet.")) {
                addSite(migrationSites, filePath, lineNum, "RULE-JAKARTA-EE-SERVLET", "javax.servlet.", lineContent, "confirmed");
            } else if (impStr.startsWith("javax.validation.")) {
                addSite(migrationSites, filePath, lineNum, "RULE-JAKARTA-EE-VALIDATION", "javax.validation.", lineContent, "confirmed");
            } else if (impStr.startsWith("javax.annotation.")) {
                addSite(migrationSites, filePath, lineNum, "RULE-JAKARTA-EE-ANNOTATION", "javax.annotation.", lineContent, "confirmed");
            } else if (impStr.contains("WebSecurityConfigurerAdapter")) {
                deprecatedSpringApis.add("WebSecurityConfigurerAdapter");
                addSite(migrationSites, filePath, lineNum, "RULE-SPRING-SECURITY-6-FILTER", "WebSecurityConfigurerAdapter", lineContent, "confirmed");
            }
        }

        // 2. Comprehensive AST Visitor
        TreePathScanner<Void, Void> scanner = new TreePathScanner<>() {
            @Override
            public Void visitClass(ClassTree node, Void p) {
                String kindStr = node.getKind().name();
                String className = node.getSimpleName().toString();
                types.add(className + " (" + kindStr + ")");

                if ("RECORD".equals(kindStr)) {
                    modernFeatures.add("record:" + className);
                } else if ("INTERFACE".equals(kindStr)) {
                    interfaces.add(className);
                }

                // Check extends clause
                if (node.getExtendsClause() != null) {
                    String superName = node.getExtendsClause().toString();
                    if (superName.contains("WebSecurityConfigurerAdapter")) {
                        deprecatedSpringApis.add("WebSecurityConfigurerAdapter");
                        long pos = positions.getStartPosition(cu, node.getExtendsClause());
                        int lineNum = (int) cu.getLineMap().getLineNumber(pos);
                        String lineContent = (lineNum <= lines.length && lineNum > 0) ? lines[lineNum - 1].trim() : superName;
                        addSite(migrationSites, filePath, lineNum, "RULE-SPRING-SECURITY-6-FILTER", "extends WebSecurityConfigurerAdapter", lineContent, "confirmed");
                    }
                }

                // Check class annotations
                if (node.getModifiers() != null) {
                    for (AnnotationTree ann : node.getModifiers().getAnnotations()) {
                        processAnnotation(ann, cu, positions, lines, filePath, imports, annotations, migrationSites);
                    }
                }

                return super.visitClass(node, p);
            }

            @Override
            public Void visitMethod(MethodTree node, Void p) {
                String methodName = node.getName().toString();
                methods.add(methodName);

                if (node.getModifiers() != null) {
                    for (AnnotationTree ann : node.getModifiers().getAnnotations()) {
                        processAnnotation(ann, cu, positions, lines, filePath, imports, annotations, migrationSites);
                    }
                }
                return super.visitMethod(node, p);
            }

            @Override
            public Void visitVariable(VariableTree node, Void p) {
                String varName = node.getName().toString();
                String varType = node.getType() != null ? node.getType().toString() : "var";
                fields.add(varName + ": " + varType);

                if (node.getModifiers() != null) {
                    for (AnnotationTree ann : node.getModifiers().getAnnotations()) {
                        processAnnotation(ann, cu, positions, lines, filePath, imports, annotations, migrationSites);
                    }
                }
                return super.visitVariable(node, p);
            }

            @Override
            public Void visitMethodInvocation(MethodInvocationTree node, Void p) {
                String invocationStr = node.getMethodSelect().toString();
                if (invocationStr.endsWith("authorizeRequests") || invocationStr.equals("authorizeRequests")) {
                    deprecatedSpringApis.add("authorizeRequests()");
                    long pos = positions.getStartPosition(cu, node);
                    int lineNum = (int) cu.getLineMap().getLineNumber(pos);
                    String lineContent = (lineNum <= lines.length && lineNum > 0) ? lines[lineNum - 1].trim() : invocationStr;
                    addSite(migrationSites, filePath, lineNum, "RULE-SPRING-SECURITY-6-FILTER", "authorizeRequests()", lineContent, "confirmed");
                } else if (invocationStr.endsWith("antMatchers") || invocationStr.equals("antMatchers")) {
                    deprecatedSpringApis.add("antMatchers()");
                    long pos = positions.getStartPosition(cu, node);
                    int lineNum = (int) cu.getLineMap().getLineNumber(pos);
                    String lineContent = (lineNum <= lines.length && lineNum > 0) ? lines[lineNum - 1].trim() : invocationStr;
                    addSite(migrationSites, filePath, lineNum, "RULE-SPRING-SECURITY-6-FILTER", "antMatchers()", lineContent, "confirmed");
                }
                return super.visitMethodInvocation(node, p);
            }

            @Override
            public Void visitSwitchExpression(SwitchExpressionTree node, Void p) {
                if (!modernFeatures.contains("switch_expression")) {
                    modernFeatures.add("switch_expression");
                }
                return super.visitSwitchExpression(node, p);
            }

            @Override
            public Void visitInstanceOf(InstanceOfTree node, Void p) {
                if (node.getPattern() != null && !modernFeatures.contains("pattern_matching_instanceof")) {
                    modernFeatures.add("pattern_matching_instanceof");
                }
                return super.visitInstanceOf(node, p);
            }
        };

        scanner.scan(cu, null);

        // Check for text blocks in source code
        if (source.contains("\"\"\"") && !modernFeatures.contains("text_blocks")) {
            modernFeatures.add("text_blocks");
        }

        // Deduplicate migration sites by (line, ruleId)
        List<Map<String, Object>> dedupedSites = deduplicateSites(migrationSites);

        // Construct JSON
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"filePath\": \"").append(escapeJson(filePath)).append("\",\n");
        sb.append("  \"packageName\": \"").append(cu.getPackageName() != null ? cu.getPackageName().toString() : "").append("\",\n");
        sb.append("  \"imports\": ").append(toJsonArray(imports)).append(",\n");
        sb.append("  \"types\": ").append(toJsonArray(types)).append(",\n");
        sb.append("  \"interfaces\": ").append(toJsonArray(interfaces)).append(",\n");
        sb.append("  \"methods\": ").append(toJsonArray(methods)).append(",\n");
        sb.append("  \"fields\": ").append(toJsonArray(fields)).append(",\n");
        sb.append("  \"annotations\": ").append(toJsonArray(annotations)).append(",\n");
        sb.append("  \"modernFeatures\": ").append(toJsonArray(modernFeatures)).append(",\n");
        sb.append("  \"deprecatedSpringApis\": ").append(toJsonArray(deprecatedSpringApis)).append(",\n");
        sb.append("  \"migrationSites\": [\n");
        for (int i = 0; i < dedupedSites.size(); i++) {
            Map<String, Object> m = dedupedSites.get(i);
            sb.append("    {\n");
            sb.append("      \"filePath\": \"").append(escapeJson((String) m.get("filePath"))).append("\",\n");
            sb.append("      \"lineNumber\": ").append(m.get("lineNumber")).append(",\n");
            sb.append("      \"ruleId\": \"").append(m.get("ruleId")).append("\",\n");
            sb.append("      \"patternMatched\": \"").append(escapeJson((String) m.get("patternMatched"))).append("\",\n");
            sb.append("      \"lineContent\": \"").append(escapeJson((String) m.get("lineContent"))).append("\",\n");
            sb.append("      \"confidence\": \"").append(m.get("confidence")).append("\"\n");
            sb.append("    }").append(i < dedupedSites.size() - 1 ? "," : "").append("\n");
        }
        sb.append("  ]\n");
        sb.append("}");
        return sb.toString();
    }

    private static void processAnnotation(
        AnnotationTree ann,
        CompilationUnitTree cu,
        SourcePositions positions,
        String[] lines,
        String filePath,
        List<String> imports,
        List<String> annotations,
        List<Map<String, Object>> migrationSites
    ) {
        String annType = ann.getAnnotationType().toString();
        annotations.add("@" + annType);

        long pos = positions.getStartPosition(cu, ann);
        int lineNum = (int) cu.getLineMap().getLineNumber(pos);
        String lineContent = (lineNum <= lines.length && lineNum > 0) ? lines[lineNum - 1].trim() : annType;

        if (annType.contains("Entity") || annType.contains("Table") || annType.contains("Id") || annType.contains("GeneratedValue") || annType.contains("Column")) {
            if (hasImportPrefix(imports, "javax.persistence")) {
                addSite(migrationSites, filePath, lineNum, "RULE-JAKARTA-EE-PERSISTENCE", "@" + annType, lineContent, "confirmed");
            }
        } else if (annType.contains("NotNull") || annType.contains("Size") || annType.contains("Valid") || annType.contains("Min") || annType.contains("Max")) {
            if (hasImportPrefix(imports, "javax.validation")) {
                addSite(migrationSites, filePath, lineNum, "RULE-JAKARTA-EE-VALIDATION", "@" + annType, lineContent, "confirmed");
            }
        } else if (annType.contains("PostConstruct") || annType.contains("PreDestroy") || annType.contains("Resource")) {
            if (hasImportPrefix(imports, "javax.annotation")) {
                addSite(migrationSites, filePath, lineNum, "RULE-JAKARTA-EE-ANNOTATION", "@" + annType, lineContent, "confirmed");
            }
        }
    }

    private static List<Map<String, Object>> deduplicateSites(List<Map<String, Object>> sites) {
        Map<String, Map<String, Object>> seen = new LinkedHashMap<>();
        for (Map<String, Object> s : sites) {
            String key = s.get("lineNumber") + ":" + s.get("ruleId");
            if (!seen.containsKey(key)) {
                seen.put(key, s);
            }
        }
        return new ArrayList<>(seen.values());
    }

    private static boolean hasImportPrefix(List<String> imports, String prefix) {
        for (String imp : imports) {
            if (imp.startsWith(prefix)) return true;
        }
        return false;
    }

    private static void addSite(List<Map<String, Object>> sites, String filePath, int lineNum, String ruleId, String pattern, String content, String conf) {
        Map<String, Object> m = new HashMap<>();
        m.put("filePath", filePath);
        m.put("lineNumber", lineNum);
        m.put("ruleId", ruleId);
        m.put("patternMatched", pattern);
        m.put("lineContent", content);
        m.put("confidence", conf);
        sites.add(m);
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    private static String toJsonArray(List<String> list) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < list.size(); i++) {
            sb.append("\"").append(escapeJson(list.get(i))).append("\"");
            if (i < list.size() - 1) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }
}
