public class BcryptCheck {
  public static void main(String[] a) {
    org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder e = new org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder();
    System.out.println("admin123 matches: " + e.matches("admin123", "$2a$10$N.ZOn9G6/YLFixAobF4lqOJ4kFPQfHx3vRZQ6vJr2QpD2vD9wM0E"));
  }
}
