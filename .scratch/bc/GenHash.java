public class GenHash {
  public static void main(String[] a) {
    org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder e = new org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder();
    String h = e.encode("admin123");
    System.out.println(h);
    System.out.println("verify: " + e.matches("admin123", h));
  }
}
